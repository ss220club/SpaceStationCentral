from pydantic import BaseModel

from .role import Role


class GuildPreview(BaseModel):
    id: str | None = None
    name: str
    icon: str | None
    banner: str | None
    owner: bool
    permissions: int
    features: list[str]


class Guild(GuildPreview):
    owner_id: int | None
    verification_level: int | None
    default_message_notifications: int | None
    roles: list[Role] | None
