from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta

from app.database.models import Player
from pydantic import BaseModel


class NewWhitelistBase(BaseModel, ABC):
    server_type: str
    duration_days: int
    valid: bool = True

    def get_expiration_time(self) -> datetime:
        return datetime.now(UTC) + timedelta(days=self.duration_days)

    @abstractmethod
    def get_player_clause(self) -> bool:
        pass

    @abstractmethod
    def get_admin_clause(self) -> bool:
        pass


class NewWhitelistBanBase(NewWhitelistBase):
    reason: str | None = None


class NewWhitelistCkey(NewWhitelistBase):
    player_ckey: str
    admin_ckey: str

    def get_player_clause(self) -> bool:
        return Player.ckey == self.player_ckey

    def get_admin_clause(self) -> bool:
        return Player.ckey == self.admin_ckey


class NewWhitelistBanCkey(NewWhitelistCkey, NewWhitelistBanBase):
    pass


class NewWhitelistDiscord(NewWhitelistBase):
    player_discord_id: str
    admin_discord_id: str

    def get_player_clause(self) -> bool:
        return Player.discord_id == self.player_discord_id

    def get_admin_clause(self) -> bool:
        return Player.discord_id == self.admin_discord_id


class NewWhitelistBanDiscord(NewWhitelistDiscord, NewWhitelistBanBase):
    pass


NewWhitelist = NewWhitelistDiscord | NewWhitelistCkey
NewWhitelistBan = NewWhitelistBanDiscord | NewWhitelistBanCkey


class WhitelistPatch(BaseModel):
    valid: bool | None = None
    expiration_time: datetime | None = None
