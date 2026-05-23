"""OPS domain models (D-AD-02, D-QI-01..04, D-PP-03).

Espone i modelli Pydantic v2 frozen utilizzati dai 4 agenti OPS di Fase 6
(AnomalyDetector, QualityInspector, ProductionPlanner, OperatorAssistant) +
i loader YAML lru_cached + il TypedDict di stato LangGraph.

Tutti i modelli sono `frozen=True`, `extra='forbid'`, e rifiutano datetime naive
(Pitfall 7 — Fase 4 cross-cutting).
"""

from sft_domain.ops.anomaly import (
    Anomaly,
    AnomalyBaseline,
    invalidate_anomaly_baselines_cache,
    load_anomaly_baselines,
)
from sft_domain.ops.citation import RagCitation
from sft_domain.ops.quality import (
    DefectType,
    QualityEvent,
    QualityVerdict,
    Severity,
)
from sft_domain.ops.schedule import (
    AssetCapacity,
    OrderSpec,
    ScheduleDraft,
    ScheduleDraftItem,
    invalidate_orders_cache,
    invalidate_capacity_cache,
    load_asset_capacity,
    load_orders,
)
from sft_domain.ops.state import OpsState

__all__ = [
    "Anomaly",
    "AnomalyBaseline",
    "AssetCapacity",
    "DefectType",
    "OpsState",
    "OrderSpec",
    "QualityEvent",
    "QualityVerdict",
    "RagCitation",
    "ScheduleDraft",
    "ScheduleDraftItem",
    "Severity",
    "invalidate_anomaly_baselines_cache",
    "invalidate_capacity_cache",
    "invalidate_orders_cache",
    "load_anomaly_baselines",
    "load_asset_capacity",
    "load_orders",
]
