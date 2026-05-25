---
tags:
  - adr
  - architecture
  - governance
---

# ADR-004 — 4-tier HITL approval

- **Status:** Accepted
- **Phase:** Phase 4 (runtime) / Phase 10 (UI)
- **Date:** 2026

## Context

Agentic actions with operational effect cannot be applied autonomously: a human
control proportional to the risk and attributable is required. Requirements:

- separation of powers by role (RBAC);
- every human decision justified and traceable (audit trail);
- read-only access for auditing, without approval power;
- no operational action applied without explicit approval.

## Decision

We adopt a **4-tier human-in-the-loop approval chain**, mapped to roles and
applied through LangGraph's `interrupt()` (see ADR-001):

- **operator** — proposes/executes routine actions within its scope;
- **technician** — approves technical and maintenance interventions;
- **shift supervisor** — approves planning and cross-team actions;
- **auditor** — read-only access to the audit trail, no approval.

The frontend enforces a minimum motivation (`MOTIVATION_MIN_LENGTH = 10`
characters) for every approval/rejection; each decision produces an immutable
`AuditRecord` with `decision_actor` (JWT sub) and `query_hash`.

Code reference:

- `packages/sft-agents/src/sft_agents/runtime/supervisor.py` — `safe_invoke`.
- `apps/factory-ui/src/app/shared/approval-card/approval-card.component.ts` —
  `MOTIVATION_MIN_LENGTH`.
- [HITL Cycle](../architecture/hitl-cycle.md).

## Consequences

**Positive**

- separation of powers and attributability of decisions (RBAC + JWT);
- immutable, motivated audit trail for every action;
- no unapproved autonomous operational action.

**Negative / trade-off**

- additional latency in the decision cycle (waiting for human approval);
- need to keep the role ↔ tier mapping consistent between runtime and UI.

Decision implemented in the runtime (Phase 4) and in the approval UI (Phase 10).
