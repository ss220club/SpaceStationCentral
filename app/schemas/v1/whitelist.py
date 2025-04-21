from abc import ABCMeta, abstractmethod
from datetime import datetime, timedelta
from typing import override

from app.core.utils import utcnow2
from app.database.models import Player
from pydantic import BaseModel


# endregion
# region Post
class NewWhitelistBase(BaseModel, metaclass=ABCMeta):
    server_type: str
    duration_days: int
    valid: bool = True

    def get_expiration_time(self) -> datetime:
        return utcnow2() + timedelta(days=self.duration_days)

    @abstractmethod
    def get_player_clause(self) -> bool:
        pass

    @abstractmethod
    def get_admin_clause(self) -> bool:
        pass


class NewWhitelistBanBase(NewWhitelistBase, metaclass=ABCMeta):
    reason: str | None = None


class NewWhitelistCkey(NewWhitelistBase):
    player_ckey: str
    admin_ckey: str

    @override
    def get_player_clause(self) -> bool:
        return Player.ckey == self.player_ckey

    @override
    def get_admin_clause(self) -> bool:
        return Player.ckey == self.admin_ckey


class NewWhitelistBanCkey(NewWhitelistCkey, NewWhitelistBanBase):
    pass


class NewWhitelistDiscord(NewWhitelistBase):
    player_discord_id: str
    admin_discord_id: str

    @override
    def get_player_clause(self) -> bool:
        return Player.discord_id == self.player_discord_id

    @override
    def get_admin_clause(self) -> bool:
        return Player.discord_id == self.admin_discord_id


class NewWhitelistBanDiscord(NewWhitelistDiscord, NewWhitelistBanBase):
    pass


NewWhitelist = NewWhitelistDiscord | NewWhitelistCkey
NewWhitelistBan = NewWhitelistBanDiscord | NewWhitelistBanCkey


# endregion
# region Patch
class WhitelistPatch(BaseModel):
    valid: bool | None = None
    expiration_time: datetime | None = None
