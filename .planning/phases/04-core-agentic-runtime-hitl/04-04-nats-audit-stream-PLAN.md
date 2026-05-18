---
phase: 04-core-agentic-runtime-hitl
plan: 04
type: execute
wave: 2
depends_on: ["04-01"]
files_modified:
  - scripts/nats-bootstrap-streams.py
  - packages/sft-agents/src/sft_agents/audit/__init__.py
  - packages/sft-agents/src/sft_agents/audit/nats_publisher.py
  - packages/sft-agents/src/sft_agents/audit/subjects.py
  - tests/integration/test_audit_stream_bootstrap.py
  - packages/sft-agents/tests/test_audit_subjects.py
autonomous: true
requirements: [CORE-08, HITL-05]
threat_refs: [T-04-NATS-Spoofed, T-04-Outbox-Drop]

must_haves:
  truths:
    - "Running `python scripts/nats-bootstrap-streams.py` exits 0 and declares `AUDIT_STREAM` with subjects `audit.actions.>`, `hitl.approvals.>`, `hitl.governor.>` and 90-day retention"
    - "Second run is idempotent (add_stream fails with BadRequestError → update_stream)"
    - "AuditNatsPublisher.publish_audit(record) publishes to subject `audit.actions.<cluster>.<agent_id>` with `record.model_dump_json().encode('utf-8')` body"
    - "Subject derivation enforces enum values (no user-controlled strings); subject_for_audit(cluster='ops', agent_id='operator-assistant') == 'audit.actions.ops.operator-assistant'"
    - "Subject derivation rejects characters outside `[a-z0-9.-_]` to prevent subject hijack"
  artifacts:
    - path: "scripts/nats-bootstrap-streams.py"
      provides: "extended in-place to declare AUDIT_STREAM in addition to SENSOR_EVENTS + AUDIT_OT"
      contains: "AUDIT_STREAM"
    - path: "packages/sft-agents/src/sft_agents/audit/nats_publisher.py"
      provides: "AuditNatsPublisher class with connect/publish/drain lifecycle"
      contains: "class AuditNatsPublisher"
    - path: "packages/sft-agents/src/sft_agents/audit/subjects.py"
      provides: "subject_for_audit + subject_for_approval + subject_for_governor + validators"
      contains: "def subject_for_audit"
  key_links:
    - from: "scripts/nats-bootstrap-streams.py"
      to: "JetStream AUDIT_STREAM"
      via: "try add_stream / except update_stream"
      pattern: "AUDIT_STREAM"
    - from: "sft_agents.audit.nats_publisher"
      to: "nats.js.JetStreamContext.publish"
      via: "subject derived from enum values"
      pattern: "js.publish"
---

<objective>
Wave 2 Plan C: extend `scripts/nats-bootstrap-streams.py` in place to declare a new JetStream stream `AUDIT_STREAM` (subjects `audit.actions.>`, `hitl.approvals.>`, `hitl.governor.>`; 90-day retention per HITL-05; FileStorage). Add a publisher class `AuditNatsPublisher` (mirrors Phase 3 ot-bridge NatsPublisher) and a subject derivation helper that prevents subject hijack (T-04-NATS-Spoofed).

Purpose: provide the NATS leg of the dual-write audit (D-56). PG is source of truth; NATS is the 90-day replica feeding ops telemetry, governor sliding window, and UI push notifications (Phase 10/11).

Output: in-place edit of nats-bootstrap-streams.py adding `AUDIT_STREAM` config + new audit/ submodule with publisher + subjects helper + integration test verifying stream declaration is idempotent.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/04-core-agentic-runtime-hitl/04-CONTEXT.md
@.planning/phases/04-core-agentic-runtime-hitl/04-RESEARCH.md
@.planning/phases/04-core-agentic-runtime-hitl/04-PATTERNS.md
@scripts/nats-bootstrap-streams.py
@services/ot-bridge/src/svc_ot_bridge/nats_publisher.py

<interfaces>
AUDIT_STREAM config (D-56 + RESEARCH §12 + PATTERNS §3.12):

```
audit_stream_cfg = {
    "name": "AUDIT_STREAM",
    "subjects": ["audit.actions.>", "hitl.approvals.>", "hitl.governor.>"],
    "retention": "LimitsPolicy",
    "max_age_ns": 90 * 24 * 3600 * 1_000_000_000,  # 90 days in nanoseconds
    "storage": "FileStorage",
    "max_msgs": -1,
    "max_bytes": -1,
    "discard": "DiscardOld",
    "num_replicas": 1,
}
```

Subjects (CONTEXT.md Claude's Discretion line 422):
- audit.actions.<cluster>.<agent_id>  — D-56 dual-write audit replica
- hitl.approvals.new.<tier>  — D-55 new approval notify
- hitl.approvals.resolved.<tier>  — D-55 approval decided notify
- hitl.governor.alert  — D-58 governor alert (no further suffix)

cluster ∈ {ops, maintenance, knowledge-curation, knowledge-training, supply}
tier ∈ {operator, supervisor, manager, safety_interlock}
agent_id from PATTERNS §3.3 list of 16 slugs (kebab-case)

Subject validator:
- ASCII lowercase, digits, hyphen, underscore, dot only
- No `*` or `>` in caller input (only in stream subjects, never in published subjects)
- Length ≤ 256 chars (NATS limit is 256)

AuditNatsPublisher API (replicates services/ot-bridge/src/svc_ot_bridge/nats_publisher.py):
- `class AuditNatsPublisher`
  - `__init__(self, nats_url: str)`
  - `async def connect(self) -> None`  — nats.connect(self._url) then jetstream() → store self._js
  - `async def publish_audit(self, record: AuditRecord) -> None` — derives subject + publishes JSON bytes
  - `async def publish_approval_new(self, approval: ApprovalRequest) -> None` — subject `hitl.approvals.new.<tier>`
  - `async def publish_approval_resolved(self, approval: ApprovalRequest) -> None` — subject `hitl.approvals.resolved.<tier>`
  - `async def publish_governor_alert(self, payload: dict) -> None` — subject `hitl.governor.alert`, payload JSON
  - `async def drain(self) -> None` — close gracefully
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 04-04-01: subject derivation helper + tests</name>
  <files>packages/sft-agents/src/sft_agents/audit/__init__.py, packages/sft-agents/src/sft_agents/audit/subjects.py, packages/sft-agents/tests/test_audit_subjects.py</files>
  <read_first>
    - services/ot-bridge/src/svc_ot_bridge/nats_publisher.py (entire file — esp. `derive_event_subject` pattern at lines 31-38)
    - .planning/phases/04-core-agentic-runtime-hitl/04-CONTEXT.md Claude's Discretion lines 421-423 (NATS subject conventions Phase 4)
    - .planning/phases/04-core-agentic-runtime-hitl/04-RESEARCH.md §Security Domain (NATS subject hijack threat — derivation from enum values only)
    - packages/sft-agents/src/sft_agents/models/enums.py (Plan 04-01 created enums)
  </read_first>
  <pattern_ref>services/ot-bridge/src/svc_ot_bridge/nats_publisher.py:31-38 (derive_event_subject pattern — replicate for audit subjects)</pattern_ref>
  <threat_ref>T-04-NATS-Spoofed</threat_ref>
  <behavior>
    - `subject_for_audit(cluster="ops", agent_id="operator-assistant")` returns `"audit.actions.ops.operator-assistant"`
    - `subject_for_audit(cluster="ops", agent_id="evil; DROP")` raises ValueError (regex rejection)
    - `subject_for_audit(cluster="badcluster", agent_id="...")` raises ValueError (cluster not in enum)
    - `subject_for_approval_new(tier=Tier.OPERATOR)` returns `"hitl.approvals.new.operator"`
    - `subject_for_approval_resolved(tier=Tier.SUPERVISOR)` returns `"hitl.approvals.resolved.supervisor"`
    - `subject_for_governor_alert()` returns `"hitl.governor.alert"` (no suffix)
    - All helpers reject input containing `*`, `>`, whitespace, or characters outside `[a-z0-9._-]`
    - `STREAM_SUBJECTS = ["audit.actions.>", "hitl.approvals.>", "hitl.governor.>"]` module constant
    - `VALID_CLUSTERS = frozenset({"ops","maintenance","knowledge-curation","knowledge-training","supply"})` module constant
  </behavior>
  <action>
    Create `packages/sft-agents/src/sft_agents/audit/__init__.py` empty for now (re-exports added in Task 04-04-02). Create `audit/subjects.py`: imports `from sft_agents.models.enums import Tier`; defines `VALID_CLUSTERS = frozenset({"ops","maintenance","knowledge-curation","knowledge-training","supply"})`; `STREAM_SUBJECTS = ("audit.actions.>", "hitl.approvals.>", "hitl.governor.>")`; `_TOKEN_RE = re.compile(r"^[a-z0-9._-]+$")`; helper `_validate_token(token: str, name: str) -> None`: if not _TOKEN_RE.fullmatch(token) raise ValueError(f"{name} contains invalid characters: {token!r}"); also reject `*` and `>` explicitly. `def subject_for_audit(*, cluster: str, agent_id: str) -> str`: assert cluster in VALID_CLUSTERS (raise ValueError); _validate_token(agent_id, "agent_id"); return f"audit.actions.{cluster}.{agent_id}". `def subject_for_approval_new(*, tier: Tier | str) -> str`: tier_val = tier.value if isinstance(tier, Tier) else tier; _validate_token(tier_val, "tier"); assert tier_val in {t.value for t in Tier}; return f"hitl.approvals.new.{tier_val}". `def subject_for_approval_resolved(*, tier)` analogous returning `hitl.approvals.resolved.{tier_val}`. `def subject_for_governor_alert() -> str`: return "hitl.governor.alert". `def validate_subject(subject: str) -> bool`: assert overall length ≤256 and ASCII safe (no `*`, `>`, whitespace). Write `test_audit_subjects.py` with tests: subject_for_audit happy path (one per cluster — 5 assertions); subject_for_audit invalid cluster raises ValueError; subject_for_audit injection attempts (`agent_id="*"`, `"a>b"`, `"a b"`, `"a;rm -rf /"`, `"audit.actions.ops.foo.bar"`) each raise ValueError; subject_for_approval_new for each Tier value (4 assertions); subject_for_governor_alert returns exactly `hitl.governor.alert`; STREAM_SUBJECTS contains the 3 wildcard subjects exactly.
  </action>
  <verify>
    <automated>cd packages/sft-agents && uv run python -c "from sft_agents.audit.subjects import subject_for_audit, subject_for_approval_new, subject_for_governor_alert, STREAM_SUBJECTS; from sft_agents.models.enums import Tier; print(subject_for_audit(cluster='ops', agent_id='operator-assistant')); print(subject_for_approval_new(tier=Tier.OPERATOR)); print(subject_for_governor_alert()); print(STREAM_SUBJECTS)" && uv run pytest tests/test_audit_subjects.py -x -v 2>&1 | tail -10</automated>
  </verify>
  <done>Subject helpers produce exact strings; ValueError raised for all injection attempts (≥5); test_audit_subjects.py green with ≥15 assertions; STREAM_SUBJECTS tuple matches AUDIT_STREAM declaration</done>
  <commit_scope>feat(04-04-nats-audit-stream-01): subject derivation helpers + injection-safe validators</commit_scope>
</task>

<task type="auto" tdd="true">
  <name>Task 04-04-02: AUDIT_STREAM bootstrap in nats-bootstrap-streams.py + AuditNatsPublisher</name>
  <files>scripts/nats-bootstrap-streams.py, packages/sft-agents/src/sft_agents/audit/__init__.py, packages/sft-agents/src/sft_agents/audit/nats_publisher.py, tests/integration/test_audit_stream_bootstrap.py</files>
  <read_first>
    - scripts/nats-bootstrap-streams.py (entire file — esp. lines 85-167: audit_ot_cfg structure, StreamConfig construction at 129-135, try add_stream / except BadRequestError / update_stream at 148-167)
    - services/ot-bridge/src/svc_ot_bridge/nats_publisher.py (entire file — class lifecycle pattern lines 60-132; publish_audit method)
    - .planning/phases/04-core-agentic-runtime-hitl/04-CONTEXT.md (D-56 retention 90d; D-58 governor alert subject)
    - packages/sft-agents/src/sft_agents/audit/subjects.py (just-created subject helpers)
    - packages/sft-agents/src/sft_agents/models/audit.py (AuditRecord — for publisher input shape)
  </read_first>
  <pattern_ref>scripts/nats-bootstrap-streams.py:85-92 (audit_ot_cfg dict — copy structure for audit_stream_cfg)</pattern_ref>
  <pattern_ref>scripts/nats-bootstrap-streams.py:129-167 (StreamConfig + try/except idempotency)</pattern_ref>
  <pattern_ref>services/ot-bridge/src/svc_ot_bridge/nats_publisher.py:60-132 (NatsPublisher class — entire lifecycle as template)</pattern_ref>
  <threat_ref>T-04-NATS-Spoofed, T-04-Outbox-Drop</threat_ref>
  <behavior>
    - `python scripts/nats-bootstrap-streams.py` first run: creates AUDIT_STREAM with 3 subjects `audit.actions.>`, `hitl.approvals.>`, `hitl.governor.>`, retention=LimitsPolicy, max_age=90 days, FileStorage, exit 0
    - Second run: catches BadRequestError, calls update_stream, exit 0 (idempotent)
    - SENSOR_EVENTS and AUDIT_OT streams (Phase 3) are still declared (no regression)
    - `AuditNatsPublisher(nats_url).connect()` connects + opens jetstream context
    - `AuditNatsPublisher.publish_audit(record)` derives subject via `subject_for_audit(cluster=record.cluster, agent_id=record.agent_id)` and publishes `record.model_dump_json().encode("utf-8")`
    - `AuditNatsPublisher.publish_approval_new(approval)` uses `subject_for_approval_new(tier=approval.tier)`
    - `AuditNatsPublisher.publish_governor_alert(payload)` uses `subject_for_governor_alert()`, payload is dict → json bytes
    - Publish failures raise; caller (Plan 04-06 AuditWriter) handles by enqueuing audit.outbox row
    - Integration test verifies AUDIT_STREAM exists with correct subjects + 90d retention after running the script against testcontainers NATS
  </behavior>
  <action>
    Edit `scripts/nats-bootstrap-streams.py` in place: add a new config dict `audit_stream_cfg` after `audit_ot_cfg` (around line 92) with name="AUDIT_STREAM", subjects=["audit.actions.>", "hitl.approvals.>", "hitl.governor.>"], retention="LimitsPolicy", max_age_days=90, storage="FileStorage", max_msgs=-1, max_bytes=-1, discard="DiscardOld", num_replicas=1. Update `all_cfg_specs` list to include audit_stream_cfg. In the StreamConfig construction block (around line 129), add construction of `cfg_audit_stream = StreamConfig(name="AUDIT_STREAM", subjects=[...], retention=RetentionPolicy.LIMITS, max_age=90 * 24 * 3600 * 1_000_000_000, storage=StorageType.FILE, max_msgs=-1, max_bytes=-1, discard=DiscardPolicy.OLD, num_replicas=1)` and append to the iteration list. The existing try add_stream → except BadRequestError → update_stream loop should iterate over all 3 configs (sensor_events, audit_ot, audit_stream) without further structural change. Preserve module docstring claim "Pitfall 3 idempotency". Now create `audit/nats_publisher.py`: imports nats + nats.js.errors; replicate ot-bridge NatsPublisher class structure: `class AuditNatsPublisher`: `__init__(self, nats_url: str)` stores url; `async def connect(self)`: `self._nc = await nats.connect(self._url); self._js = self._nc.jetstream(); log.info("audit_publisher_connected", url=self._url)`. `async def publish_audit(self, record: AuditRecord) -> None`: subject = `subject_for_audit(cluster=record.cluster, agent_id=record.agent_id)`; payload = `record.model_dump_json().encode("utf-8")`; await `self._js.publish(subject, payload)`; structlog log on success at debug; re-raise on exception. `async def publish_approval_new(self, approval: ApprovalRequest)`: subject = `subject_for_approval_new(tier=approval.tier)`; payload = `approval.model_dump_json().encode("utf-8")`; publish. `async def publish_approval_resolved(self, approval)` analogous. `async def publish_governor_alert(self, payload: dict)`: subject = `subject_for_governor_alert()`; await js.publish(subject, json.dumps(payload).encode("utf-8")). `async def drain(self)`: `if self._nc is not None: await self._nc.drain()`. Module-level logger via structlog. Update `audit/__init__.py` to re-export `AuditNatsPublisher` + the 4 subject helpers + STREAM_SUBJECTS. Write `tests/integration/test_audit_stream_bootstrap.py` with `@pytest.mark.integration`: launch testcontainers `nats:2.10-alpine` container with `-js` JetStream flag; set NATS_URL env to container's bound port; run `scripts/nats-bootstrap-streams.py` via subprocess; assert exit 0; connect via nats.connect + jetstream; `info = await js.stream_info("AUDIT_STREAM")`; assert `info.config.subjects == ["audit.actions.>", "hitl.approvals.>", "hitl.governor.>"]`; assert `info.config.max_age == 90 * 24 * 3600 * 1_000_000_000`; assert `info.config.storage == StorageType.FILE`. Then run script again; assert exit 0 (idempotent — update_stream branch hit). Add second test using `AuditNatsPublisher` against the same container: build a minimal AuditRecord (cluster="ops", agent_id="operator-assistant", decision="auto", motivation=None, approval_id=None, action_id=uuid4(), thread_id="t1", action_type="TEST", evidence_panel=<minimal valid>, budget_snapshot=<minimal>); call `publish_audit(record)`; consume from AUDIT_STREAM via pull consumer; assert payload JSON deserializes to record matching agent_id and decision fields.
  </action>
  <verify>
    <automated>cd "/media/federicocalo/D1/prj/Smart Factory Transformation" && python -c "import ast; ast.parse(open('scripts/nats-bootstrap-streams.py').read()); ast.parse(open('packages/sft-agents/src/sft_agents/audit/nats_publisher.py').read()); print('ast ok')" && grep -n "AUDIT_STREAM" scripts/nats-bootstrap-streams.py | grep -v '^#' && grep -n "audit.actions\.>\|hitl.approvals\.>\|hitl.governor\.>" scripts/nats-bootstrap-streams.py | grep -v '^#'</automated>
  </verify>
  <done>scripts/nats-bootstrap-streams.py declares AUDIT_STREAM with 3 wildcard subjects + 90d retention; AuditNatsPublisher class implements publish_audit / publish_approval_new / publish_approval_resolved / publish_governor_alert / drain; integration test fixture exists; existing SENSOR_EVENTS + AUDIT_OT declarations preserved</done>
  <commit_scope>feat(04-04-nats-audit-stream-02): declare audit_stream + auditnatspublisher class with subject derivation</commit_scope>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| AuditRecord.cluster + agent_id → NATS subject | Pydantic-validated record fields cross into NATS subject string (derivation is server-controlled, not user-controlled) |
| bootstrap script → NATS JetStream config | Idempotent declarative config; second run is update-only |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-NATS-Spoofed | Spoofing | audit/subjects.py | mitigate | Subject derivation reads enum-bounded values only (VALID_CLUSTERS + Tier enum); _validate_token regex rejects `*`, `>`, whitespace; injection tests in test_audit_subjects.py |
| T-04-NATS-Spoofed (wildcard publish) | Spoofing | nats_publisher.py | mitigate | Publishers use derived subjects only (never accept user-supplied subject strings); STREAM_SUBJECTS wildcards live in bootstrap config only |
| T-04-Outbox-Drop | Repudiation | nats_publisher.publish_audit | mitigate | Publisher raises on failure; AuditWriter (Plan 04-06) catches and enqueues audit.outbox; this plan establishes the failure-surfacing contract |
| T-04-NATS-Spoofed (ACL) | Spoofing | NATS subject ACL | accept | Phase 11 governance — Plan 04-04 ships subject conventions only; account-level ACLs deferred to deployment hardening |
</threat_model>

<verification>
- `python scripts/nats-bootstrap-streams.py` exits 0 on first AND second run
- `nats stream ls` (or `js.stream_info("AUDIT_STREAM")`) shows AUDIT_STREAM with 3 wildcard subjects + 90d retention
- `uv run pytest packages/sft-agents/tests/test_audit_subjects.py -x` green
- `uv run pytest tests/integration/test_audit_stream_bootstrap.py -m integration` green (testcontainers NATS)
- SENSOR_EVENTS + AUDIT_OT streams (Phase 3) still declared (no regression — `js.stream_info("SENSOR_EVENTS")` returns valid info)
</verification>

<success_criteria>
- CORE-08 NATS substrate: AUDIT_STREAM ready for dual-write audit replica (Plan 04-06 AuditWriter consumes this)
- HITL-05 NATS leg: 90-day retention enforced at stream level matching CONTEXT.md D-56
- T-04-NATS-Spoofed mitigated: subject derivation cannot be hijacked by user-supplied strings
- Phase 3 streams (SENSOR_EVENTS, AUDIT_OT) preserved — no regression on `ot-bridge`
- Wave 3 unblocked (Plan 04-06 AuditWriter can import AuditNatsPublisher)
</success_criteria>

<output>
Create `.planning/phases/04-core-agentic-runtime-hitl/04-04-SUMMARY.md` documenting:
- AUDIT_STREAM config (subjects, retention, storage)
- Subject derivation helpers + injection-test count
- AuditNatsPublisher public API
- Idempotency proof (second run)
</output>