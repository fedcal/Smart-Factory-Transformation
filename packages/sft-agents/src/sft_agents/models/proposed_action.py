"""ProposedAction Pydantic model with deterministic UUID derivation (Pitfall 6).

The id is sha256-derived from (thread_id, action_type, canonical_json(args)) so identical
inputs produce identical UUIDs — required for idempotency across retries.
"""

from __future__ import annotations

import hashlib
import json
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, Field

from sft_agents.models.enums import ActionType


class ProposedAction(BaseModel):
    """An action proposed by an agent prior to HITL / Safety Interlock review.

    The deterministic id makes the same logical action across replays match the
    same approval row in PG (idempotent on retries).
    """

    model_config = {"frozen": True, "extra": "forbid"}

    id: Annotated[UUID, Field(description="Deterministic UUID from sha256(thread_id|action_type|canonical_args)")]
    action_type: Annotated[ActionType, Field(description="Categorical action label")]
    target_subject: Annotated[
        str | None,
        Field(default=None, description="NATS subject if this action publishes (None otherwise)"),
    ] = None
    args: Annotated[dict[str, Any], Field(description="JSON-serializable action arguments")]

    @classmethod
    def from_payload(
        cls,
        thread_id: str,
        action_type: ActionType | str,
        args: dict[str, Any],
        target_subject: str | None = None,
    ) -> "ProposedAction":
        """Build a ProposedAction with a deterministic id (Pitfall 6).

        The id is derived from:
            sha256(thread_id + "|" + action_type + "|" + canonical_json(args))[:32]
        reinterpreted as a UUID hex string.
        """
        if isinstance(action_type, ActionType):
            at_value = action_type.value
        else:
            at_value = str(action_type)
            action_type = ActionType(at_value)

        canonical = json.dumps(args, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        digest = hashlib.sha256(
            f"{thread_id}|{at_value}|{canonical}".encode("utf-8")
        ).hexdigest()
        det_uuid = UUID(hex=digest[:32])
        return cls(
            id=det_uuid,
            action_type=action_type,
            target_subject=target_subject,
            args=args,
        )
