"""OpsState — TypedDict di stato per il LangGraph subgraph OPS.

Usato come `state_schema` per i 4 agenti OPS:
    AnomalyDetector / OperatorAssistant / QualityInspector / ProductionPlanner.

Total=False perche' ogni nodo del grafo aggiorna solo un subset dei campi.
Tutti i campi sono optional al runtime; la presenza/assenza riflette il
progresso del flusso (es. `verdict` popolato solo dopo QualityInspector).
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from sft_domain.ops.anomaly import Anomaly
from sft_domain.ops.quality import QualityEvent, QualityVerdict
from sft_domain.ops.schedule import ScheduleDraft


class OpsState(TypedDict, total=False):
    """Stato condiviso del LangGraph OPS subgraph.

    Tutti i campi sono optional (total=False). Ogni nodo legge/scrive
    solo i campi rilevanti al proprio compito; LangGraph mergia gli
    aggiornamenti in modo immutabile.
    """

    # ---------- Routing / contesto ----------
    target_agent: Literal[
        "anomaly_detector",
        "operator_assistant",
        "quality_inspector",
        "production_planner",
    ]
    """Quale agente OPS deve gestire la chiamata."""

    window_minutes: int
    """Finestra temporale (in minuti) per query/scheduling/anomaly windowing."""

    strategy: Literal["spt", "edd"]
    """Strategia di scheduling richiesta (ProductionPlanner)."""

    query: str
    """Query NL dell'operator/manager (OperatorAssistant)."""

    user_roles: list[str]
    """Ruoli del chiamante (operator, supervisor, manager, ...)."""

    thread_id: str
    """Identificatore della conversazione LangGraph."""

    # ---------- ReAct loop ----------
    messages: list[Any]
    """Cronologia messaggi LangChain (BaseMessage)."""

    tool_results: list[dict[str, Any]]
    """Risultati delle invocazioni dei tool ReAct."""

    iteration_count: int
    """Numero di iterazioni ReAct (cap a max_iterations)."""

    evidence_citations: list[dict[str, Any]]
    """Citazioni RAG raccolte durante il flusso (serializzazione RagCitation)."""

    # ---------- Output per dominio ----------
    anomalies: list[Anomaly]
    """Anomalie rilevate (AnomalyDetector)."""

    quality_event: QualityEvent
    """Evento qualita' in input al QualityInspector."""

    verdict: QualityVerdict
    """Verdetto qualita' emesso (QualityInspector output)."""

    schedule_draft: ScheduleDraft
    """Bozza di scheduling (ProductionPlanner output)."""

    escalation_payload: dict[str, Any]
    """Payload escalation per il tier supervisor/manager (HITL)."""
