import datetime
from typing import TYPE_CHECKING, Callable

from pydantic import BaseModel
from sqlmodel.sql.expression import SelectOfScalar

from app.database.models import Player


class NewWhitelistBase(BaseModel):
    server_type: str
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


NEW_WHITELIST_TYPES =  NewWhitelistDiscord | NewWhitelistCkey
NEW_WHITELIST_BAN_TYPES =  NewWhitelistBanDiscord | NewWhitelistBanCkey


def resolve_whitelist_type(new_wl: NEW_WHITELIST_TYPES) -> tuple[Callable[[NEW_WHITELIST_TYPES], SelectOfScalar], Callable[[NEW_WHITELIST_TYPES], SelectOfScalar]]:
    match new_wl:
        case NewWhitelistInternal():
            return (lambda new_wl: Player.id == new_wl.player_id, lambda new_wl: Player.id == new_wl.admin_id)
        case NewWhitelistDiscord():
            return (lambda new_wl: Player.discord_id == new_wl.player_discord_id, lambda new_wl: Player.discord_id == new_wl.admin_discord_id)
        case NewWhitelistCkey():
            return (lambda new_wl: Player.ckey == new_wl.player_ckey, lambda new_wl: Player.ckey == new_wl.admin_ckey)
        case _:
            raise TypeError(
                "Someone added a new whitelist type without a case in resolve_whitelist_type")


class WhitelistPatch(BaseModel):
    valid: bool | None = None
    expiration_time: datetime.datetime | None = None
