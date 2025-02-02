import datetime
from pydantic import BaseModel

class NewWhitelistBase(BaseModel):
    wl_type: str
    duration_days: int
    valid: bool = True

    def get_expiration_time(self) -> datetime.datetime:
        return datetime.datetime.now() + datetime.timedelta(days=self.duration_days)


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
