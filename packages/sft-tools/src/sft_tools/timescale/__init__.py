"""TimescaleDB Tools: query proxy per sensor_events hypertable.

Espone:
    QueryTimescaleTool  — read-only asyncpg query tool per sensor_events
    TIMESCALE_TOOLS     — lista [QueryTimescaleTool()]
"""

from sft_tools.timescale.query import QueryTimescaleTool

TIMESCALE_TOOLS = [QueryTimescaleTool()]

__all__ = [
    "QueryTimescaleTool",
    "TIMESCALE_TOOLS",
]
