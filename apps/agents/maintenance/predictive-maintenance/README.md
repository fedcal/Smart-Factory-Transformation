# mnt-predictive-maintenance

Maintenance cluster LangGraph node: **PredictiveMaintenance** (D-PM-04).

## Role

Estimates Remaining Useful Life (RUL) for textile assets (looms, spinning,
dyeing, warping) using the committed Ridge C-MAPSS model (`sft-ml` package,
07-03). Triggered event-driven by AnomalyDetector via NATS JetStream publish
on `maintenance.predict.<asset_id>` (Open Q1 Option a — thin additive extension
to AnomalyDetector, Phase 6 contract preserved).

## Cross-cluster trigger (AD -> PM)

AnomalyDetector emits a NATS message on `maintenance.predict.<asset_id>` ONLY
when `decision == Decision.AUTO AND severity in {major, critical}`. The payload
is `PredictRequest` (JSON). The `pm-consumer` durable pull subscriber receives
the message and invokes `PredictiveMaintenance.__call__`.

## Invocation

```python
from mnt_predictive_maintenance import PredictiveMaintenance

agent = PredictiveMaintenance(
    pool=pool,
    audit_writer=audit_writer,
    asset_registry=[asset_loom_01],
)
result = await agent({"asset_id": "LOOM-01", "triggered_by_action_id": "<uuid>"})
# result["rul_estimate"] is a RULEstimate (frozen Pydantic)
```

## HITL gate

When `health_index < 0.3`, `escalate_to_supervisor` is called BEFORE the
audit row is written (Pitfall §3). The `recommended_action` field carries a
human-readable IT intervention message with asset_id, rul_cycles, and SOP family.

## Audit chain

`evidence_panel.tool_calls[0].args.triggered_by_action_id` == AnomalyDetector
audit row's `action_id` UUID — resolvable via SQL JOIN (MNT-06).

## Requirements satisfied

- MNT-01: RUL estimation per asset from C-MAPSS Ridge model adapted to textile
- MNT-06: Audit chain `triggered_by_action_id` link to upstream AD alert
