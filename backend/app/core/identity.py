from dataclasses import dataclass
from typing import Annotated

from fastapi import Header, Request

from app.core.config import get_settings
from app.core.errors import PermissionDeniedError


VALID_ROLES = {"viewer", "operator", "reviewer", "admin"}
WRITE_ROLES = {"operator", "reviewer", "admin"}
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "viewer": {"read"},
    "operator": {"read", "operate", "ack_alert", "manage_config"},
    "reviewer": {"read", "review", "manage_bad_case"},
    "admin": {
        "read",
        "operate",
        "ack_alert",
        "review",
        "manage_bad_case",
        "manage_config",
        "admin",
    },
}


@dataclass(frozen=True)
class Actor:
    name: str
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def parse_actor(actor_header: str | None, role_header: str | None) -> Actor:
    name = _clean_header(actor_header) or "system"
    role = (_clean_header(role_header) or "operator").lower()
    if role not in VALID_ROLES:
        role = "viewer"
    return Actor(name=name, role=role)


def get_actor(
    request: Request,
    actor_header: Annotated[str | None, Header(alias="X-SmartTraffic-Actor")] = None,
    role_header: Annotated[str | None, Header(alias="X-SmartTraffic-Role")] = None,
) -> Actor:
    actor = parse_actor(actor_header, role_header)
    request.state.actor = actor
    return actor


def require_permission(actor: Actor, permission: str) -> None:
    if get_settings().auth_mode != "strict":
        return
    if permission not in ROLE_PERMISSIONS.get(actor.role, set()):
        raise PermissionDeniedError(
            f"role '{actor.role}' is not allowed to perform '{permission}'"
        )


def actor_context(actor: Actor) -> dict[str, str]:
    return {"actor": actor.name, "role": actor.role}


def _clean_header(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
