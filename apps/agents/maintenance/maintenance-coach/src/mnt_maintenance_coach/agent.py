"""MaintenanceCoach LangGraph agent — placeholder (implemented in Task 3).

This module stub allows __init__.py to import without error during Task 2.
Full implementation in Task 3.
"""

from __future__ import annotations

# Placeholders that will be replaced in Task 3
AGENT_ID: str = "maintenance-coach"
CLUSTER: str = "maintenance"
_MESSAGE_TRIM_THRESHOLD: int = 50
_MAX_STEPS: int = 100


def _trim_messages(messages: list, threshold: int) -> list:
    """Trim message list to bounded size, keeping system messages + tail.

    When ``len(messages) <= threshold``, returns messages unchanged.
    When above threshold, keeps:
      - All system-type messages from the first 5 messages (preserve context)
      - The last ``(threshold - n_system_kept)`` non-system messages

    This ensures the system prompt is never discarded while bounding
    token usage (07-PATTERNS.md Section 6 risk callout #1).

    Args:
        messages: Current message list.
        threshold: Maximum number of messages to keep.

    Returns:
        Trimmed message list of length <= threshold + n_system_kept.
    """
    if len(messages) <= threshold:
        return messages

    # Preserve system messages from the first 5 slots
    system_msgs = [
        m for m in messages[:5] if getattr(m, "type", None) == "system"
    ]
    n_system = len(system_msgs)
    tail_size = threshold - n_system
    tail = messages[-tail_size:] if tail_size > 0 else []

    return system_msgs + tail


class MaintenanceCoach:
    """Placeholder — implemented in Task 3."""

    def __init__(self, **kwargs) -> None:
        raise NotImplementedError("MaintenanceCoach is implemented in Task 3")


def build_coach_graph(**kwargs):
    """Placeholder — implemented in Task 3."""
    raise NotImplementedError("build_coach_graph is implemented in Task 3")


__all__ = [
    "AGENT_ID",
    "CLUSTER",
    "MaintenanceCoach",
    "_MESSAGE_TRIM_THRESHOLD",
    "_trim_messages",
    "build_coach_graph",
]
