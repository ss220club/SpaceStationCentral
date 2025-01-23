from pydantic import BaseModel

from app.database.models import Player, Whitelist, WhitelistBase


class NewWhitelistBase(BaseModel):
    duration_days: int
    valid: bool = True


class NewWhitelistBanBase(NewWhitelistBase):
    reason: str | None = None

class NewWhitelistInternal(NewWhitelistBase):
    player_id: int
    admin_id: int

class NewWhitelistBanInternal(NewWhitelistInternal, NewWhitelistBanBase):
    pass

class NewWhitelistCkey(NewWhitelistBase):
    player_ckey: str
    admin_ckey: str


class NewWhitelistBanCkey(NewWhitelistCkey, NewWhitelistBanBase):
    pass


class NewWhitelistDiscord(NewWhitelistBase):
    player_discord_id: str
    admin_discord_id: str


class NewWhitelistBanDiscord(NewWhitelistDiscord, NewWhitelistBanBase):
    pass
