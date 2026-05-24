---
phase: 08-agents-knowledge-training
plan: "05"
subsystem: training-coach
tags: [training, quiz, hitl, deterministic-scoring, dynamic-difficulty, rag, supervisor]
dependency_graph:
  requires: ["08-00a", "08-00b", "sft-agents.models.enums.ActionType.TRAINING_SESSION/TRAINING_SIGNOFF"]
  provides: ["trn_training_coach.TrainingCoach", "trn_training_coach.quiz.score_session", "trn_training_coach.difficulty.DifficultyAdaptor"]
  affects: ["audit.actions TRAINING_SESSION", "audit.actions TRAINING_SIGNOFF", "knowledge cluster tests"]
tech_stack:
  added: ["trn-training-coach package", "pydantic frozen models for quiz/session/result"]
  patterns: ["W4/CR-02 interrupt-then-audit ordering", "CR-03 approval_id=None", "Pitfall §3 LLM-free scoring", "generate-at-session-start (RESEARCH Open Q2)", "D-X-03 SOP frontmatter persona roles"]
key_files:
  created:
    - apps/agents/knowledge/training-coach/src/trn_training_coach/quiz.py
    - apps/agents/knowledge/training-coach/src/trn_training_coach/difficulty.py
    - apps/agents/knowledge/training-coach/src/trn_training_coach/models.py
    - apps/agents/knowledge/training-coach/src/trn_training_coach/agent.py
    - apps/agents/knowledge/training-coach/src/trn_training_coach/metadata.py
    - apps/agents/knowledge/training-coach/src/trn_training_coach/prompts.py
  modified:
    - apps/agents/knowledge/training-coach/src/trn_training_coach/__init__.py
    - apps/agents/knowledge/training-coach/tests/test_quiz_scoring.py
    - apps/agents/knowledge/training-coach/tests/test_difficulty.py
    - apps/agents/knowledge/training-coach/tests/test_hitl_lifecycle.py
    - apps/agents/knowledge/training-coach/pyproject.toml
    - uv.lock
decisions:
  - "W4/CR-02: TRAINING_SESSION and TRAINING_SIGNOFF both written AFTER interrupt() returns on pass path (not before) to prevent LangGraph replay double-write"
  - "Pitfall §3: score_session is a pure function with zero LLM imports — scoring is index comparison only"
  - "CR-03: approval_id=None on TRAINING_SIGNOFF row (never fabricate UUID for pending HITL)"
  - "D-X-03: VALID_PERSONA_ROLES from SOP frontmatter, graceful degradation for unknown roles (no registry)"
  - "RESEARCH Open Q2: quiz questions generated at session start via LLM, then frozen as MCQSession (generate-at-session-start)"
  - "TRN-05: every MCQQuestion carries source_uri from RAG citation; fallback questions carry synthetic source_uri"
  - "Pattern G: ImportError fallback shim for langgraph.types.interrupt in test environments"
metrics:
  duration: "35 min"
  completed_date: "2026-05-24"
  tasks_completed: 2
  files_created: 6
  files_modified: 6
  tests_added: 16
---

# Phase 08 Plan 05: TrainingCoach Agent Summary

**One-liner:** Deterministic MCQ quiz delivery with LLM-only generation, dynamic difficulty (D-TC-02), and supervisor HITL sign-off (interrupt-then-audit W4/CR-02 ordering).

## What Was Built

### Task 1: Deterministic quiz + dynamic difficulty + frozen models (D-TC-01/02)

- **quiz.py**: `MCQQuestion` (frozen Pydantic, options 2..6, `correct_answer_index`, `source_uri` TRN-05, `difficulty`) and `MCQSession` (frozen, `session_id`, `persona_role`, `questions`, `answers`). `score_session()` is a pure function: index equality only, no async, no LLM import (Pitfall §3 / T-08-09).
- **difficulty.py**: `DifficultyAdaptor.next_difficulty(current, answer_correct=True/False)` and module-level `next_difficulty()`. Rises on correct (easy→medium→hard), falls on wrong (hard→medium→easy), capped at both extremes. Returns new string — never mutates input.
- **models.py**: `TrainingSession` and `CompetencyResult` frozen Pydantic models. `TrainingSession.citations` holds `RagCitation` objects for TRN-05 traceability.
- **Tests**: 10 tests in `test_quiz_scoring.py` + `test_difficulty.py` rewritten from Wave 0 scaffold to concrete passing contracts.

### Task 2: TrainingCoach node with single-interrupt HITL sign-off (D-TC-03)

- **agent.py**: `TrainingCoach.__call__()` implements the W4/CR-02 corrected audit ordering:
  - **PASSING path**: RAG retrieval → LLM quiz generation (frozen) → deterministic `score_session()` → `interrupt(SUPERVISOR)` directly in `__call__` → AFTER resume: write `TRAINING_SESSION` then `TRAINING_SIGNOFF` (both with `approval_id=None`, CR-03).
  - **FAILING path**: deterministic scoring → write `TRAINING_SESSION` immediately → return. No interrupt, no `TRAINING_SIGNOFF`.
  - LLM is called ONLY in `_generate_quiz_questions()`, never in scoring. `score_session()` has no LLM dependency.
  - Fallback questions provided when LLM unavailable (degraded mode, always `source_uri` present for TRN-05).
- **metadata.py**: `AGENT_ID="training-coach"`, `TOOL_INVENTORY`, `DATA_SOURCES` (Qdrant training/sop, SOP frontmatter roles), `KPIS_IMPACTED`, `build_trn05_evidence_panel()`.
- **prompts.py**: `build_quiz_generation_prompt()` for closed MCQ generation with explicit `correct_option_index` and `source_uri` per question.
- **\_\_init\_\_.py**: exports `TrainingCoach`, `DifficultyAdaptor`, `MCQQuestion`, `MCQSession`, `score_session`, `next_difficulty`, `TrainingSession`, `CompetencyResult`.
- **pyproject.toml**: added `sft-agents` dependency (workspace source).
- **Tests**: 6 tests in `test_hitl_lifecycle.py` rewritten from Wave 0 scaffold to concrete passing contracts verifying W4/CR-02/CR-03 invariants.

## Test Results

All 16 tests pass:
- `test_quiz_scoring.py`: 5 tests (perfect/partial/zero score, no-LLM guard, threshold 0.80)
- `test_difficulty.py`: 5 tests (rises/falls/ceiling/floor caps, full session trajectory)
- `test_hitl_lifecycle.py`: 6 tests (pass: 1 TRAINING_SIGNOFF, 1 TRAINING_SESSION, 0 writes before interrupt, approval_id=None; fail: no interrupt, no TRAINING_SIGNOFF, 1 TRAINING_SESSION)

## Deviations from Plan

None — plan executed exactly as written. The W4/CR-02 ordering note in the plan (PATTERNS stub was pre-W4; action text was authoritative) was implemented correctly: both TRAINING_SESSION and TRAINING_SIGNOFF are written AFTER `interrupt()` returns on the pass path.

## Security Notes (Threat Model)

- **T-08-09 (Tampering — prompt injection)**: Mitigated. `score_session()` is LLM-free; `correct_answer_index` is frozen at generation time and cannot be overwritten by operator input. Verified: `quiz.py` has no LLM/interrupt imports.
- **T-08-10 (Repudiation — competency sign-off)**: Mitigated. Single `TRAINING_SIGNOFF` row written after supervisor resume; `approval_id=None` (CR-03).

## Threat Flags

None — no new network endpoints or auth paths introduced. All audit writes go through the existing `audit_writer` interface (established in Phase 4).

## Known Stubs

None — all data flows are wired. The `retrieval_pipeline=None` path has a graceful fallback to `_fallback_questions()` (LLM unavailable scenario, still TRN-05 compliant with synthetic `source_uri`).

## Self-Check: PASSED

All 6 created files verified present. Both task commits verified in git log:
- `645d766`: Task 1 (quiz.py, difficulty.py, models.py, tests)
- `5291156`: Task 2 (agent.py, metadata.py, prompts.py, __init__.py, test_hitl_lifecycle.py, pyproject.toml, uv.lock)
