---
status: partial
phase: 08-agents-knowledge-training
source: [08-VERIFICATION.md]
started: 2026-05-24T14:30:00Z
updated: 2026-05-24T14:30:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Flusso HITL completo ShiftHandover su LangGraph reale
expected: Con checkpointer PostgreSQL reale, `handover_id` resta stabile tra le 3 esecuzioni del nodo (prima esecuzione + 2 resume); l'audit registra esattamente 2x HANDOVER_SIGNOFF (approval_id=None) + 1x HANDOVER_DRAFT, nessuna scrittura prima del primo interrupt, nessun double-write su replay.
result: [pending]

### 2. Migrazione 010 su TimescaleDB di sviluppo
expected: `make migrate-timescale` applica 010 in modo idempotente; il CHECK constraint `audit_actions_action_type_chk` include i 7 nuovi valori Phase 8 senza regressioni sui valori legacy Phase 1-7.
result: [pending]

### 3. Smoke test LLM reale (Qwen2.5/Ollama)
expected: Qualità semantica accettabile per generazione quiz (TrainingCoach) e traduzione IT→EN (DocumentationSynthesizer), con anchor preservati e citazioni source_uri presenti.
result: [pending]

### 4. Approval queue dual-supervisor
expected: `SELECT` su `audit.actions` dopo un handover completato mostra le 2 righe di sign-off correlate allo stesso `handover_id` con le motivazioni corrette (outgoing/incoming supervisor).
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
