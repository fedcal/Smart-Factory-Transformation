"""Operations agent: production planning and scheduling optimization (D-PP-01..04).

Public entrypoint: :class:`ProductionPlanner`. Constructed with injected
collaborators (rag_pipeline, audit_writer, queue_writer, nats); invoked as
``await planner(state)`` where ``state`` is the LangGraph AgentState dict
containing ``strategy``, ``horizon_days``, ``user_roles``, ``thread_id``.
"""

from ops_production_planner.agent import ProductionPlanner
from ops_production_planner.models import PlanRequest, PlanResponse

__version__ = "0.1.0"

__all__ = ["ProductionPlanner", "PlanRequest", "PlanResponse"]
