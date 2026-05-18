---
phase: 04-core-agentic-runtime-hitl
plan: 04
subsystem: nats-audit-stream
tags: [nats, jetstream, audit, hitl, dual-write, wave-2, subjects, publisher]
requires: ["04-01"]
provides:
  - "JetStream `AUDIT_STREAM` declaration with 3 wildcard subjects (audit.actions.>, hitl.approvals.>, hitl.governor.>) and 90-day retention (D-56, HITL-05)"
  - "AuditNatsPublisher class: publish_audit / publish_approval_new / publish_approval_resolved / publish_governor_alert / drain"
  - "Subject derivation helpers (subject_for_audit, subject_for_approval_new/resolved, subject_for_governor_alert) with enum-bounded inputs + token regex (T-04-NATS-Spoofed mitigation)"
  - "Module-level constants STREAM_SUBJECTS (tuple) + VALID_CLUSTERS (frozenset) — single source of truth shared by bootstrap script and publisher"
  - "Idempotency contract for `scripts/nats-bootstrap-streams.py`: second run hits BadRequestError → update_stream branch → exit 0"
affects:
  - "Unblocks Plan 04-06 (AuditWriter dual-write — imports AuditNatsPublisher)"
  - "Unblocks Plan 04-07 (FastAPI api-gateway — uses subject helpers to publish hitl.approvals.* notifications)"
  - "Unblocks Plan 04-06 (Governor background task — uses subject_for_governor_alert + publish_governor_alert)"
threat_refs: [T-04-NATS-Spoofed, T-04-Outbox-Drop]
tech_stack:
  added:
    - "testcontainers (already in root dev deps) — driving NATS integration test fixture"
  patterns:
    - "Subject derivation from enum-bounded + regex-validated inputs (mirrors Phase 3 derive_event_subject — `services/ot-bridge/src/svc_ot_bridge/nats_publisher.py:31-38`)"
    - "try add_stream / except BadRequestError → update_stream idempotency (Pitfall 3 mitigation; same pattern Phase 3 `nats-bootstrap-streams.py:148-167`)"
    - "publish_* re-raises on failure → caller (AuditWriter Plan 04-06) handles outbox retry (T-04-Outbox-Drop contract)"
    - "Module-scoped testcontainers fixture with skip-on-no-docker (no dependency on compose stack)"
key_files:
  created:
    - "packages/sft-agents/src/sft_agents/audit/__init__.py — re-exports AuditNatsPublisher + 5 subject helpers + STREAM_SUBJECTS + VALID_CLUSTERS"
    - "packages/sft-agents/src/sft_agents/audit/subjects.py — derivation helpers + injection-safe validators (147 lines)"
    - "packages/sft-agents/src/sft_agents/audit/nats_publisher.py — AuditNatsPublisher class (134 lines)"
    - "packages/sft-agents/tests/test_audit_subjects.py — 41 unit tests covering happy paths + 12-input injection matrix (260 lines)"
    - "packages/sft-agents/tests/test_audit_publisher.py — 12 unit tests using mock_nats_js fixture (234 lines)"
    - "tests/integration/test_audit_stream_bootstrap.py — 3 testcontainers-driven integration tests (220 lines)"
  modified:
    - "scripts/nats-bootstrap-streams.py — added audit_stream_cfg + cfg_audit_stream StreamConfig; Rule 3 fix: changed all three streams' max_age from nanoseconds to seconds (nats-py 2.14 semantic)"
decisions:
  - "Dot (.) is excluded from `_TOKEN_RE` — agent_id `audit.actions.ops.evil` would otherwise pass token validation and let an attacker hijack the subject hierarchy. Plan spec was ambiguous (`[a-z0-9._-]`); chose the tighter regex defensively (T-04-NATS-Spoofed)"
  - "`subject_for_approval_new(tier=...)` accepts both `Tier` enum members AND string values — required because some callers hydrate `tier` directly from a DB row where it is stored as text. String inputs still pass `_validate_token` + `_VALID_TIER_VALUES` set membership"
  - "`AuditNatsPublisher.drain()` clears `self._nc` + `self._js` to `None` after drain so re-use after drain raises a clear AttributeError instead of a silent NATS error"
  - "Integration test uses module-scoped testcontainers (one NATS container shared across 3 tests) — keeps the suite under 2 seconds while still proving idempotency via 2 sequential script invocations"
metrics:
  duration: "single session"
  completed_date: "2026-05-18"
  tasks_completed: 2
  files_created: 6
  files_modified: 1
  unit_tests_added: 53      # 41 subjects + 12 publisher
  integration_tests_added: 3
  total_test_count: "137 unit (was 125 → +12 + 41 already counted in 137) + 3 integration"
  injection_assertions: 14
---

# Phase 4 Plan 04: NATS AUDIT_STREAM Substrate Summary

Plan 04-04 (Wave 2 C) lands the NATS leg of the dual-write audit (D-56): a new
JetStream stream `AUDIT_STREAM` with 90-day retention and three wildcard
subjects (`audit.actions.>`, `hitl.approvals.>`, `hitl.governor.>`), plus the
`AuditNatsPublisher` class with injection-safe subject derivation. Phase 3
streams (`SENSOR_EVENTS`, `AUDIT_OT`) remain declared with no behavioral
regression — and a pre-existing `max_age` units bug in `nats-bootstrap-streams.py`
was repaired in the process. Wave 3 plans (04-06 AuditWriter, 04-07 api-gateway,
Governor background task) can now `from sft_agents.audit import AuditNatsPublisher`.

## Tasks Completed

| Task | Name                                           | Commits                        | Files                                                                                                                                                                                       |
| ---- | ---------------------------------------------- | ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1    | Subject derivation helpers + injection tests   | `ef8fb19` (RED), `c757a28` (GREEN) | audit/__init__.py, audit/subjects.py, tests/test_audit_subjects.py                                                                                                                          |
| 2    | AUDIT_STREAM bootstrap + AuditNatsPublisher    | `5226bd2` (RED), `7137277` (GREEN) | scripts/nats-bootstrap-streams.py, audit/nats_publisher.py, audit/__init__.py, tests/test_audit_publisher.py, tests/integration/test_audit_stream_bootstrap.py |

TDD applied per task: red commit ships failing tests under `pytest.importorskip`,
green commit lands implementation + behavioral assertions.

## Verification Results

```bash
$ python3 -c "import ast; ast.parse(open('scripts/nats-bootstrap-streams.py').read()); ast.parse(open('packages/sft-agents/src/sft_agents/audit/nats_publisher.py').read()); print('ast ok')"
ast ok

$ grep -n 'AUDIT_STREAM' scripts/nats-bootstrap-streams.py | grep -v '^#'
10:    AUDIT_STREAM   — audit.actions.> + hitl.approvals.> + hitl.governor.>
98:        "name": "AUDIT_STREAM",
123:        print("AUDIT_STREAM: would create/update")
164:        name="AUDIT_STREAM",

$ grep -nE 'audit\.actions\.>|hitl\.approvals\.>|hitl\.governor\.>' scripts/nats-bootstrap-streams.py
10:    AUDIT_STREAM   — audit.actions.> + hitl.approvals.> + hitl.governor.>
99:        "subjects": ["audit.actions.>", "hitl.approvals.>", "hitl.governor.>"],
165:        subjects=["audit.actions.>", "hitl.approvals.>", "hitl.governor.>"],

$ cd packages/sft-agents && uv run --extra dev pytest tests/ --tb=short
137 passed, 13 skipped in 0.26s

$ uv run --extra dev python -c "from sft_agents.audit.subjects import subject_for_audit, subject_for_approval_new, subject_for_governor_alert, STREAM_SUBJECTS; from sft_agents.models.enums import Tier; print(subject_for_audit(cluster='ops', agent_id='operator-assistant')); print(subject_for_approval_new(tier=Tier.OPERATOR)); print(subject_for_governor_alert()); print(STREAM_SUBJECTS)"
audit.actions.ops.operator-assistant
hitl.approvals.new.operator
hitl.governor.alert
('audit.actions.>', 'hitl.approvals.>', 'hitl.governor.>')

$ cd ../.. && uv run --group dev pytest tests/integration/test_audit_stream_bootstrap.py
3 passed, 1 warning in 2.01s

$ uv run --group dev ruff check scripts/nats-bootstrap-streams.py packages/sft-agents/src/sft_agents/audit/ tests/integration/test_audit_stream_bootstrap.py packages/sft-agents/tests/test_audit_subjects.py packages/sft-agents/tests/test_audit_publisher.py
All checks passed!
```

## Success Criteria

- [x] CORE-08 NATS substrate: `AUDIT_STREAM` ready for dual-write audit replica (Plan 04-06 AuditWriter can consume) — confirmed by integration test `test_bootstrap_creates_audit_stream`
- [x] HITL-05 NATS leg: 90-day retention enforced at stream level matching CONTEXT.md D-56 — `cfg.max_age == 90 * 24 * 3600` (seconds) verified against testcontainers NATS
- [x] T-04-NATS-Spoofed mitigated: subject derivation cannot be hijacked by user-supplied strings — 14 injection assertions in `test_audit_subjects.py` (12 parametrized + 2 dot-hierarchy + tier injection)
- [x] Phase 3 streams (`SENSOR_EVENTS`, `AUDIT_OT`) preserved — regression assertions inside `test_bootstrap_creates_audit_stream`
- [x] Wave 3 unblocked (Plan 04-06 AuditWriter can `from sft_agents.audit import AuditNatsPublisher`) — confirmed by public API re-exports in `audit/__init__.py`

## Public API (Final)

The `sft_agents.audit` subpackage exposes 8 symbols flat:

| Category    | Symbols                                                                                |
| ----------- | -------------------------------------------------------------------------------------- |
| Publisher   | `AuditNatsPublisher`                                                                   |
| Helpers (4) | `subject_for_audit`, `subject_for_approval_new`, `subject_for_approval_resolved`, `subject_for_governor_alert` |
| Validators (1) | `validate_subject`                                                                  |
| Constants (2) | `STREAM_SUBJECTS`, `VALID_CLUSTERS`                                                  |

## Mechanical Enforcement (T-04-NATS-Spoofed)

| Validator             | Location                  | Enforces                                                                                                       |
| --------------------- | ------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `_TOKEN_RE`           | audit/subjects.py L70     | Single hierarchy level: `^[a-z0-9_-]+$` (dot deliberately excluded vs plan spec — defense-in-depth)             |
| `VALID_CLUSTERS`      | audit/subjects.py L31-39  | 5 D-53 cluster names only — rejects spoofed cluster strings                                                    |
| `_VALID_TIER_VALUES`  | audit/subjects.py L60     | Mirrors `Tier` enum values — rejects spoofed tier strings                                                      |
| `_FORBIDDEN_SUBJECT_CHARS` | audit/subjects.py L66-67 | Forbids `*`, `>`, whitespace in final assembled subject (defense-in-depth)                                |
| `_MAX_SUBJECT_LEN=256` | audit/subjects.py L57    | NATS server cap                                                                                                |

## AuditNatsPublisher Public API

```python
class AuditNatsPublisher:
    def __init__(self, nats_url: str) -> None: ...
    async def connect(self) -> None: ...
    async def publish_audit(self, record: AuditRecord) -> None: ...
    async def publish_approval_new(self, approval: ApprovalRequest) -> None: ...
    async def publish_approval_resolved(self, approval: ApprovalRequest) -> None: ...
    async def publish_governor_alert(self, payload: dict[str, Any]) -> None: ...
    async def drain(self) -> None: ...
```

Failure semantics: every `publish_*` re-raises on NATS error so the caller
(Plan 04-06 AuditWriter) can enqueue an `audit.outbox` row. The publisher
deliberately does NOT swallow exceptions (T-04-Outbox-Drop contract).

## Idempotency Proof

The bootstrap script's idempotency is verified by `test_bootstrap_is_idempotent`:

1. Module-scoped testcontainers NATS container starts fresh.
2. First subprocess run of `scripts/nats-bootstrap-streams.py` → exit 0, all
   three streams (`SENSOR_EVENTS`, `AUDIT_OT`, `AUDIT_STREAM`) created.
3. Second subprocess run of the same script → exit 0; `add_stream`
   raises `BadRequestError` (stream exists) → script falls through to
   `update_stream` branch which succeeds. stdout contains either `created`
   or `updated` for every stream.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] Pre-existing `max_age` units bug in `nats-bootstrap-streams.py`**

- **Found during:** Task 2 GREEN — first integration-test run against fresh
  `nats:2.10-alpine` returned `BadRequestError code=400 err_code=10025
  description='invalid JSON'` for `SENSOR_EVENTS`, before Plan 04-04 code even
  ran for `AUDIT_STREAM`.
- **Issue:** Phase 3 committed `scripts/nats-bootstrap-streams.py` (commit
  `d11b91f`) passes `max_age` to `StreamConfig` in nanoseconds (e.g.
  `7 * 24 * 3600 * 1_000_000_000`). `nats-py` 2.14 expects `max_age` in
  **seconds** (float) on the dataclass — it multiplies by `1e9` itself at
  JSON-serialization time. Passing nanoseconds produces a `max_age` of ~`1e24`
  ns on the wire, which the server rejects as invalid JSON. This affected all
  three streams (`SENSOR_EVENTS`, `AUDIT_OT`, and the new `AUDIT_STREAM`).
- **Fix:** Changed all three `StreamConfig(max_age=…)` calls from nanoseconds
  to seconds. Added inline comment explaining the nats-py 2.14 semantic so
  future authors don't regress.
- **Files modified:** `scripts/nats-bootstrap-streams.py`
- **Commit:** `7137277`
- **Note:** This bug means the original `feat(03-04-bridge-wiring)` commit
  shipped a non-functional bootstrap script. The integration test added by
  this plan (`tests/integration/test_audit_stream_bootstrap.py`) now also
  serves as a regression guard for SENSOR_EVENTS + AUDIT_OT — see Threat Flags
  below for the surface this exposed.

### Plan ambiguity resolved defensively

**2. [Rule 2 - Critical functionality] Token regex tightened (no dots)**

- **Found during:** Task 1 RED, while writing injection-test matrix.
- **Plan spec said:** "_validate_token regex rejects `*`, `>`, whitespace …
  outside `[a-z0-9._-]`" — the regex class includes dot.
- **Issue:** If dot is allowed inside a single NATS hierarchy token, then an
  attacker controlling `agent_id` could submit
  `audit.actions.ops.attacker-controlled-target` and have the publisher emit
  the message under `audit.actions.ops.audit.actions.ops.attacker-…`. While
  the wildcard subscription pattern is the same, downstream consumers that
  filter on full subject string would mis-attribute the message.
- **Fix:** Excluded `.` from `_TOKEN_RE` (kept `_` and `-`). Test
  `TestAgentIdInjection::test_extra_dot_hierarchy_rejected` enforces the
  decision. The full subject string is built by joining tokens with `.` —
  there is no legitimate need for dots inside any one token.
- **Files modified:** `packages/sft-agents/src/sft_agents/audit/subjects.py`
  (regex literal); `packages/sft-agents/tests/test_audit_subjects.py`
  (injection test).

### Style auto-fixes

**3. [Rule 1 - Bug] Ruff `from __future__` + `UTC` import**

- Ruff prefers `from datetime import UTC, datetime` (Python 3.12+) over the
  legacy `from datetime import datetime, timezone; UTC = timezone.utc`. Applied
  with `ruff check --fix`; manually removed the now-redundant `UTC = UTC` line
  that ruff left behind.
- **Files modified:** `packages/sft-agents/tests/test_audit_publisher.py`,
  `tests/integration/test_audit_stream_bootstrap.py`.
- **Commit:** rolled into `7137277`.

## Threat Flags

The Rule 3 fix exposed one new surface flag worth recording for the verifier:

| Flag                    | File                          | Description                                                                                                                                  |
| ----------------------- | ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| threat_flag: regression | `scripts/nats-bootstrap-streams.py` | Phase 3 SENSOR_EVENTS + AUDIT_OT declarations were non-functional pre-Plan-04-04 (max_age units bug). Now repaired, but Phase 3's load tests + ot-bridge live-publish path against the broken bootstrap should be re-verified in Phase 11 CI. |

No STRIDE register entries flipped from `mitigate` to `accept`:

- T-04-NATS-Spoofed: mechanically enforced via `_TOKEN_RE` + `VALID_CLUSTERS`
  + `_VALID_TIER_VALUES` + `validate_subject`.
- T-04-Outbox-Drop: contract established (`publish_*` re-raises). The
  outbox-retry side is Plan 04-06's responsibility.

## Self-Check: PASSED

- `scripts/nats-bootstrap-streams.py` — modified, contains `AUDIT_STREAM` declaration + 3 wildcard subjects (verified by `grep`)
- `packages/sft-agents/src/sft_agents/audit/__init__.py` — created, re-exports AuditNatsPublisher + helpers (verified by `python -c "from sft_agents.audit import …"`)
- `packages/sft-agents/src/sft_agents/audit/subjects.py` — created (verified by ast parse + 41 tests)
- `packages/sft-agents/src/sft_agents/audit/nats_publisher.py` — created (verified by ast parse + 12 tests)
- `packages/sft-agents/tests/test_audit_subjects.py` — created, 41 tests pass
- `packages/sft-agents/tests/test_audit_publisher.py` — created, 12 tests pass
- `tests/integration/test_audit_stream_bootstrap.py` — created, 3 tests pass against testcontainers nats:2.10-alpine
- Commits `ef8fb19`, `c757a28`, `5226bd2`, `7137277` — verified via `git log --oneline -10`
