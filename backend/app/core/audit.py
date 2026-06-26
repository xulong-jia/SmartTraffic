from typing import Any

from app.core.identity import Actor
from app.core.logging import get_logger


def audit_log(
    action: str,
    *,
    actor: Actor,
    resource_type: str,
    resource_id: str | None = None,
    outcome: str = "success",
    details: dict[str, Any] | None = None,
) -> None:
    payload = {
        "audit": True,
        "action": action,
        "actor": actor.name,
        "role": actor.role,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "outcome": outcome,
        "details": details or {},
    }
    get_logger("app.audit").info("audit_event", extra=payload)


def actor_tag(actor: Actor) -> str:
    return f"actor:{actor.name}"


def append_actor_tag(tags: list[str] | None, actor: Actor) -> list[str]:
    items = list(tags or [])
    if actor.name == "system":
        return items
    tag = actor_tag(actor)
    if tag not in items:
        items.append(tag)
    return items
