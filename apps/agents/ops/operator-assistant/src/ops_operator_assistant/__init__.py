"""Operations agent: real-time operator decision support on the factory floor.

Public API:
    - ``OperatorAssistantAgent``: ReAct orchestrator (D-OA-01..04).
    - ``OperatorChatRequest`` / ``OperatorChatResponse``: API contract.
    - ``detect_language``: deterministic IT/EN language detector (D-OA-03).
    - ``validate_or_replan``: post-LLM citation validator (D-OA-04).
"""

from ops_operator_assistant.lang_detect import detect_language
from ops_operator_assistant.models import OperatorChatRequest, OperatorChatResponse
from ops_operator_assistant.validators import validate_or_replan

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    """Lazy-import the agent so importing the package never pulls langgraph."""
    if name == "OperatorAssistantAgent":
        from ops_operator_assistant.agent import OperatorAssistantAgent  # noqa: PLC0415

        return OperatorAssistantAgent
    raise AttributeError(
        f"module 'ops_operator_assistant' has no attribute {name!r}"
    )


__all__ = [
    "OperatorAssistantAgent",
    "OperatorChatRequest",
    "OperatorChatResponse",
    "detect_language",
    "validate_or_replan",
]
