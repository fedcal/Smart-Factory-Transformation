"""Operations agent: quality control signal analysis and defect reporting.

Exports the public API of the QualityInspector agent:
    - ``grade_quality_event``: pure LLM grading function (D-QI-02).
    - ``QualityInspector``: orchestrator class (NATS consumer + grader + HITL).
"""

from ops_quality_inspector.grader import grade_quality_event

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    """Lazy import QualityInspector to avoid hard dependency at import time."""
    if name == "QualityInspector":
        from ops_quality_inspector.agent import QualityInspector  # noqa: PLC0415

        return QualityInspector
    raise AttributeError(f"module 'ops_quality_inspector' has no attribute {name!r}")


__all__ = ["QualityInspector", "grade_quality_event"]
