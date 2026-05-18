"""replay_thread — re-execute an agent thread from PG checkpoint + audit log.

Phase 4 best-effort determinism (CORE-10, HITL-08):
    - Tool calls are FROZEN to recorded ``evidence_panel.tool_calls`` (no real
      tool execution) — this is the strong determinism guarantee for Phase 4.
    - LLM calls: with ``fake_llm`` given, recompute a canonical prompt_hash
      from the recorded ``input_summary`` + ``tool_calls`` and compare against
      ``EvidencePanel.prompt_hash``. Mismatch → ``divergence_reason`` set.

Audit write semantics (T-04-Audit-Tamper):
    - ``write_audit=False`` (default) → dry run, returns ``replayed_audit_ids=None``
    - ``write_audit=True`` → emits new ``audit.actions`` rows with:
        * ``action_type='REPLAY:<orig>'`` (auditor SQL filter trivial)
        * ``evidence_panel.input_summary='[REPLAY of <orig_action_id>] ...'``
        * ``decision=Decision.AUTO`` (system-initiated; tampering-distinct via prefix)
        * ``approval_id=None`` (auto decisions require approval_id IS NULL)

Action-bounded replay (HITL-08 rollback substrate):
    - ``action_id=<UUID>`` truncates the replay AFTER the matching audit row
      (inclusive). Useful for "rewind agent state to just before action X" flows.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID, uuid4

import structlog
from pydantic import BaseModel, Field, field_validator

from sft_agents.memory.episodic import EpisodicReplay
from sft_agents.models.audit import AuditRecord
from sft_agents.models.enums import Decision
from sft_agents.models.evidence import EvidencePanel, ToolCall

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Pydantic frozen models — ReplayedAgentStep + ReplayResult
# ---------------------------------------------------------------------------


def _tz_aware(v: datetime) -> datetime:
    """Reject naive datetime (Pitfall 7)."""
    if v.tzinfo is None:
        raise ValueError(
            f"Datetime field must be tz-aware, got naive: {v!r}. "
            "Use datetime.now(timezone.utc)."
        )
    return v


class ReplayedAgentStep(BaseModel):
    """A single step in the replay timeline (CORE-10).

    Captures the recorded audit row + the result of re-execution + any
    divergence signals (prompt_hash mismatch).
    """

    model_config = {"frozen": True, "extra": "forbid"}

    step_index: Annotated[int, Field(ge=0, description="Zero-based step index")]
    recorded_action: Annotated[
        AuditRecord, Field(description="The original audit row being replayed")
    ]
    replayed_state_delta: Annotated[
        dict[str, Any],
        Field(
            default_factory=dict,
            description="Approximation of state changes from re-execution",
        ),
    ]
    divergence_reason: Annotated[
        str | None,
        Field(
            default=None,
            description="Why this step diverged (None when matched)",
        ),
    ] = None
    llm_prompt_hash_match: Annotated[
        bool,
        Field(
            description=(
                "True when prompt_hash matches recorded (or fake_llm not given). "
                "False on divergence."
            )
        ),
    ]
    tool_calls_match: Annotated[
        bool,
        Field(
            description=(
                "True by construction — tool calls are deterministic from "
                "the recorded evidence_panel.tool_calls."
            )
        ),
    ]


class ReplayResult(BaseModel):
    """Replay outcome envelope (CORE-10).

    Returned by :func:`replay_thread`. Frozen so callers cannot mutate.
    """

    model_config = {"frozen": True, "extra": "forbid"}

    thread_id: Annotated[str, Field(min_length=1)]
    replayed_steps: Annotated[
        list[ReplayedAgentStep],
        Field(default_factory=list, description="Step-by-step replay output"),
    ]
    divergence_at_step: Annotated[
        int | None,
        Field(
            default=None,
            description="First step index with non-None divergence_reason; None if all match",
        ),
    ] = None
    recorded_audit_ids: Annotated[
        list[UUID],
        Field(default_factory=list, description="audit_id of each replayed audit row"),
    ]
    replayed_audit_ids: Annotated[
        list[UUID] | None,
        Field(
            default=None,
            description="New audit row ids when write_audit=True; None on dry-run",
        ),
    ] = None
    ts_replay_start: Annotated[
        datetime, Field(description="UTC tz-aware replay start timestamp")
    ]
    ts_replay_end: Annotated[
        datetime, Field(description="UTC tz-aware replay end timestamp")
    ]

    @field_validator("ts_replay_start", "ts_replay_end")
    @classmethod
    def _check_tz(cls, v: datetime) -> datetime:
        return _tz_aware(v)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _hash_prompt(input_summary: str, tool_calls: list[ToolCall]) -> str:
    """Compute a canonical sha256 hex of the prompt content.

    The hash is deterministic across processes: it canonicalizes the
    ``input_summary`` plus a normalized JSON projection of each tool call
    (name + args + result) so re-execution with the same recorded inputs
    yields the same hash.

    Args:
        input_summary: EvidencePanel.input_summary.
        tool_calls: Recorded tool calls (ordered).

    Returns:
        64-char sha256 hex string.
    """
    payload = {
        "input_summary": input_summary,
        "tool_calls": [
            {
                "name": tc.name,
                "args": tc.args,
                "result": tc.result,
            }
            for tc in tool_calls
        ],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _truncate_at_action(
    records: list[AuditRecord], action_id: UUID | None
) -> list[AuditRecord]:
    """Truncate records AFTER the first match of action_id (inclusive).

    If action_id is not found, returns the full list unchanged (best-effort —
    the caller is responsible for verifying the action existed).
    """
    if action_id is None:
        return records
    for idx, rec in enumerate(records):
        if rec.action_id == action_id:
            return records[: idx + 1]
    return records


def _build_replay_audit_record(*, original: AuditRecord) -> AuditRecord:
    """Build a new audit row tagged 'REPLAY:' (T-04-Audit-Tamper distinction).

    The replay row preserves cluster/agent/thread for forensics but signals
    its origin via:
        - ``action_type='REPLAY:<original>'``
        - ``evidence_panel.input_summary='[REPLAY of <id>] <original_summary>'``
        - ``decision=Decision.AUTO`` + ``approval_id=None``
    """
    prefix = f"[REPLAY of {original.action_id}] "
    # Cap to EvidencePanel.input_summary max_length=500 to satisfy validator
    body = original.evidence_panel.input_summary[: 500 - len(prefix)]
    new_evidence = original.evidence_panel.model_copy(
        update={"input_summary": prefix + body}
    )
    return AuditRecord(
        id=uuid4(),
        ts=datetime.now(UTC),
        action_id=uuid4(),
        agent_id=original.agent_id,
        thread_id=original.thread_id,
        cluster=original.cluster,
        action_type=f"REPLAY:{original.action_type}",
        evidence_panel=new_evidence,
        decision=Decision.AUTO,
        decision_actor=None,
        motivation=None,
        budget_snapshot=original.budget_snapshot,
        approval_id=None,
    )


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


async def replay_thread(
    thread_id: str,
    *,
    pool: Any,
    checkpointer: Any,
    fake_llm: Any | None = None,
    action_id: UUID | None = None,
    write_audit: bool = False,
    audit_writer: Any | None = None,
) -> ReplayResult:
    """Re-execute an agent thread from PG checkpoint + audit log (CORE-10, HITL-08).

    Args:
        thread_id: The thread_id to replay (e.g. ``ops.operator-assistant.<uuid>``).
        pool: asyncpg.Pool (or compatible mock) used by EpisodicReplay.
        checkpointer: AsyncPostgresSaver (or compatible mock) — currently consulted
            for diagnostics; Phase 4 tool replay reads tool calls from the audit
            log directly. Required arg so the API is stable as full state restore
            lands in Phase 11.
        fake_llm: Optional BaseChatModel for LLM re-invocation. When provided,
            prompt_hash is recomputed and compared to the recorded value. When
            ``None``, the LLM step is skipped (``llm_prompt_hash_match=True``).
        action_id: If given, replay STOPS AFTER reaching the recorded action
            with that id (inclusive). Useful for "rollback before X" flows.
        write_audit: If True, emit new audit rows tagged ``REPLAY:`` via
            ``audit_writer.write(record)``. ``replayed_audit_ids`` will contain
            the new row ids. If False (default), dry-run only.
        audit_writer: Required when ``write_audit=True``. AuditWriter-shaped
            object exposing ``async write(AuditRecord)``.

    Returns:
        :class:`ReplayResult` with step-by-step divergence report.

    Raises:
        ValueError: When ``write_audit=True`` but ``audit_writer`` is None.
    """
    if write_audit and audit_writer is None:
        raise ValueError(
            "write_audit=True requires audit_writer (got None). "
            "Pass an AuditWriter-shaped object with `async write(AuditRecord)`."
        )

    ts_replay_start = datetime.now(UTC)
    episodic = EpisodicReplay(pool=pool)
    records = await episodic.replay_thread(thread_id)
    records = _truncate_at_action(records, action_id)

    replayed_steps: list[ReplayedAgentStep] = []
    replayed_audit_ids: list[UUID] | None = [] if write_audit else None
    divergence_at_step: int | None = None

    for idx, record in enumerate(records):
        evidence = record.evidence_panel
        # Tool calls are always deterministic — we replay from the recorded
        # evidence_panel.tool_calls and never invoke the real tool.
        tool_calls_match = True

        # LLM divergence detection (only when fake_llm is given).
        if fake_llm is None:
            llm_match = True
            divergence_reason: str | None = None
        else:
            canonical = await _hash_prompt(
                evidence.input_summary, evidence.tool_calls
            )
            if canonical == evidence.prompt_hash:
                llm_match = True
                divergence_reason = None
            else:
                llm_match = False
                divergence_reason = (
                    f"prompt_hash divergence at step {idx}: "
                    f"recorded={evidence.prompt_hash[:8]}... "
                    f"recomputed={canonical[:8]}..."
                )

        replayed_state_delta = {
            "messages_appended": [],
            "tool_calls": [
                {"name": tc.name, "args": tc.args, "result": tc.result}
                for tc in evidence.tool_calls
            ],
            "model": evidence.model,
        }

        step = ReplayedAgentStep(
            step_index=idx,
            recorded_action=record,
            replayed_state_delta=replayed_state_delta,
            divergence_reason=divergence_reason,
            llm_prompt_hash_match=llm_match,
            tool_calls_match=tool_calls_match,
        )
        replayed_steps.append(step)

        if divergence_at_step is None and divergence_reason is not None:
            divergence_at_step = idx

        if write_audit and audit_writer is not None:
            new_record = _build_replay_audit_record(original=record)
            await audit_writer.write(new_record)
            assert replayed_audit_ids is not None  # narrow for type checker
            replayed_audit_ids.append(new_record.id)

    ts_replay_end = datetime.now(UTC)

    logger.info(
        "replay_thread_complete",
        thread_id=thread_id,
        records_count=len(records),
        divergence_at_step=divergence_at_step,
        write_audit=write_audit,
        action_id=str(action_id) if action_id else None,
    )

    return ReplayResult(
        thread_id=thread_id,
        replayed_steps=replayed_steps,
        divergence_at_step=divergence_at_step,
        recorded_audit_ids=[r.id for r in records],
        replayed_audit_ids=replayed_audit_ids,
        ts_replay_start=ts_replay_start,
        ts_replay_end=ts_replay_end,
    )
