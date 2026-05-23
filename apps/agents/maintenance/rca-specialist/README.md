# mnt-rca-specialist

Maintenance agent: Root Cause Analysis Specialist using the 5-Why methodology
with citation grounding and always-supervisor HITL gate.

## Role

`RCASpecialist` is the second business-logic agent of the maintenance cluster
(MNT-02 + MNT-05). It implements the **form-based 5-Why methodology** where:

- Every WHY step is backed by at least one retrieved document (citation grounding
  via Phase 5 `rag_search` + `traverse_graph` tools).
- Every document URI is verified to exist in PostgreSQL `documents` table before
  the chain is considered valid (Open Q5 resolved as full PG lookup, audit-friendly).
- Every corrective action passes through HITL supervisor approval (literal success
  criterion #2 from ROADMAP Phase 7, D-RCA-02).

## 5-Why Schema (D-RCA-01)

- `WhyStep`: question, answer, citations (min 1), confidence [0,1]
- `RCAChain`: exactly 5 named why_1..why_5 fields + root_cause + corrective_action_recommendation
- Field names are explicit + auditable; no dynamic list of steps

## ALWAYS Supervisor Gate (D-RCA-02)

Every successful `RCAChain` — and every exhausted retry path — triggers
`escalate_to_supervisor` before writing the audit row. There is no severity-based
branching; the literal success criterion reads "supervisor" unconditionally.

## Retry Policy

The ReAct loop catches `ValidationError | MissingCitationError | OrphanCitationError`
and re-prompts up to 2 times (3 total attempts). On exhaustion it escalates with
`reason='rca_validation_exhausted'` and carries the best attempted chain in the
evidence panel for forensic review.

## Tools

- `rag_search` — Phase 5 hybrid retrieval over SOPs, manuals, troubleshooting guides
- `traverse_graph` — Phase 5 Neo4j traversal (Machine → Part → FailureMode → SOP)
- `escalate_to_supervisor` — Phase 6 HITL interrupt (ALWAYS invoked, D-RCA-02)
