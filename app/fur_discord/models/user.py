from typing import Any, Optional

from pydantic import BaseModel


class User(BaseModel):
    id: str = None
    username: str
    avatar: str
    discriminator: str
    public_flags: int
    flags: int
    banner: Any | None
    accent_color: int
    global_name: str
    avatar_decoration_data: Any | None
    banner_color: str
    mfa_enabled: bool
    clan: Any | None
    locale: str
    premium_type: int
