"""sft_agents.replay — deterministic replay from PG checkpoint + audit log (CORE-10, HITL-08).

Public surface:
    replay_thread       — async function re-executing an agent thread
    ReplayResult        — Pydantic frozen result envelope
    ReplayedAgentStep   — per-step replay record (recorded action + divergence)

Phase 4 best-effort determinism (CONTEXT.md Pitfall §5):
    - Tool calls are FROZEN to recorded outputs (no real tool execution)
    - LLM calls: if ``fake_llm`` given, prompt_hash is recomputed and compared
      to the recorded hash; if absent, the LLM step is skipped entirely
    - Full determinism (frozen tool outputs end-to-end) → Phase 11

Write modes:
    - ``write_audit=False`` (default): dry-run replay, no new audit rows
    - ``write_audit=True``: emits new audit rows with ``action_type='REPLAY:<orig>'``
      and ``evidence_panel.input_summary='[REPLAY of <id>] ...'`` so auditors can
      filter replay-written rows from originals (T-04-Audit-Tamper distinction)
"""

from __future__ import annotations

from sft_agents.replay.from_checkpoint import (
    ReplayedAgentStep,
    ReplayResult,
    replay_thread,
)

__all__ = [
    "ReplayResult",
    "ReplayedAgentStep",
    "replay_thread",
]
