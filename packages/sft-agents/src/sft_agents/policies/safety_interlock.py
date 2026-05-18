"""SafetyInterlockMiddleware — pre-tool whitelist enforcement (HITL-03, D-58, T-04-Whitelist-Bypass).

Loads ``safety-interlock.yaml`` and rejects any :class:`ProposedAction` whose
``target_subject`` matches a forbidden NATS glob OR whose ``action_type`` is in
``forbidden_action_types``.

Glob semantics (NATS → fnmatch translation):
    - ``cmd.plc.setpoint.>`` matches ``cmd.plc.setpoint.<anything>`` (one or more
      tokens) — implemented as ``startswith("cmd.plc.setpoint.")``.
    - ``cmd.firmware.deploy`` (no wildcard) matches exactly that subject.

Audit trail (T-04-Whitelist-Bypass):
    On rejection, the middleware writes an ``interlock_reject`` AuditRecord via
    the injected AuditWriter BEFORE raising :class:`SafetyInterlockRejection`.
    The audit row is the forensic evidence; the exception terminates the agent
    path.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import structlog
import yaml

from sft_agents.models.budget import BudgetSnapshot
from sft_agents.models.enums import Decision
from sft_agents.models.evidence import EvidencePanel
from sft_agents.models.proposed_action import ProposedAction

if TYPE_CHECKING:
    from sft_agents.audit.writer import AuditWriter
    from sft_agents.models.audit import AuditRecord

logger = structlog.get_logger(__name__)

_DEFAULT_YAML_PATH = Path(__file__).parent / "safety-interlock.yaml"


class SafetyInterlockRejection(Exception):
    """Raised when SafetyInterlockMiddleware blocks a ProposedAction."""

    def __init__(
        self,
        *,
        action_id: Any,
        action_type: str,
        reason: str,
    ) -> None:
        self.action_id = action_id
        self.action_type = action_type
        self.reason = reason
        super().__init__(
            f"SafetyInterlockRejection action_id={action_id} "
            f"action_type={action_type}: {reason}"
        )


class SafetyInterlockMiddleware:
    """Pre-tool whitelist check; load YAML once on init."""

    def __init__(
        self,
        *,
        yaml_path: Path | None = None,
        audit_writer: "AuditWriter | None" = None,
    ) -> None:
        path = yaml_path or _DEFAULT_YAML_PATH
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        # Pre-compute prefix matches for NATS `.>` globs; keep literals as-is.
        raw_subjects = list(data.get("forbidden_subjects", []) or [])
        self._forbidden_prefixes: list[str] = []
        self._forbidden_literals: frozenset[str] = frozenset()
        literals: list[str] = []
        for entry in raw_subjects:
            entry_s = str(entry)
            if entry_s.endswith(".>"):
                self._forbidden_prefixes.append(entry_s[:-1])  # keep trailing "."
            elif entry_s.endswith(".*"):
                self._forbidden_prefixes.append(entry_s[:-1])
            else:
                literals.append(entry_s)
        self._forbidden_literals = frozenset(literals)
        self._forbidden_action_types: frozenset[str] = frozenset(
            str(t) for t in data.get("forbidden_action_types", []) or []
        )
        self._audit_writer = audit_writer
        logger.info(
            "safety_interlock_loaded",
            yaml_path=str(path),
            forbidden_subject_count=(
                len(self._forbidden_prefixes) + len(self._forbidden_literals)
            ),
            forbidden_action_type_count=len(self._forbidden_action_types),
        )

    def _match(self, action: ProposedAction) -> str | None:
        """Return a reason string if the action matches the whitelist; else None."""
        if action.action_type.value in self._forbidden_action_types:
            return f"action_type={action.action_type.value} in forbidden_action_types"
        if action.target_subject:
            subject = action.target_subject
            if subject in self._forbidden_literals:
                return f"target_subject={subject!r} in forbidden_subjects (literal)"
            for prefix in self._forbidden_prefixes:
                if subject.startswith(prefix):
                    return (
                        f"target_subject={subject!r} matches forbidden prefix "
                        f"{prefix}>"
                    )
        return None

    async def check(
        self,
        action: ProposedAction,
        *,
        agent_id: str,
        thread_id: str,
        cluster: str,
        evidence_panel: EvidencePanel,
        budget_snapshot: BudgetSnapshot,
    ) -> None:
        """Audit + raise if forbidden; pass-through (return None) otherwise."""
        reason = self._match(action)
        if reason is None:
            return None

        # Build interlock_reject audit row.
        from sft_agents.models.audit import AuditRecord  # noqa: PLC0415

        record = AuditRecord(
            id=uuid4(),
            ts=datetime.now(timezone.utc),
            action_id=action.id,
            agent_id=agent_id,
            thread_id=thread_id,
            cluster=cluster,
            action_type=action.action_type.value,
            evidence_panel=evidence_panel,
            decision=Decision.INTERLOCK_REJECT,
            decision_actor=None,
            motivation=None,
            budget_snapshot=budget_snapshot,
            approval_id=None,
        )
        if self._audit_writer is not None:
            await self._audit_writer.write(record)
        else:
            logger.warning(
                "safety_interlock_rejection_unaudited",
                action_id=str(action.id),
                reason=reason,
            )
        logger.info(
            "safety_interlock_rejection",
            action_id=str(action.id),
            action_type=action.action_type.value,
            reason=reason,
        )
        raise SafetyInterlockRejection(
            action_id=action.id,
            action_type=action.action_type.value,
            reason=reason,
        )
