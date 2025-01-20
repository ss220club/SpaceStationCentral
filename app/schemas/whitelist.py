from pydantic import BaseModel

from app.database.models import Player, Whitelist, WhitelistBase


class NewWhitelistBase(BaseModel):
    duration_days: int


class NewWhitelistBanBase(NewWhitelistBase):
    reason: str | None = None


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
