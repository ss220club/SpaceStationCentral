from datetime import datetime, timedelta
from secrets import token_urlsafe

from sqlmodel import Field, SQLModel


class Player(SQLModel, table=True):
    # Actually is a pretty big int. Is way **too** big for a lot of software to handle
    discord_id: str = Field(primary_key=True)
    ckey: str | None = Field(unique=True, index=True)


class OneTimeToken(SQLModel, table=True):
    id: int= Field(default=None, primary_key=True)
    ckey: str = Field(unique=True, index=True)
    token: str = Field(unique=True, default_factory=lambda: token_urlsafe(32), index=True)
    expiry: datetime = Field(
        default_factory=lambda: datetime.now() + timedelta(minutes=5))


class WhitelistBase(SQLModel):
    id: int= Field(default=None, primary_key=True)
    player_id: str = Field(foreign_key="player.discord_id", index=True)
    wl_type: str = Field(default="default")
    admin_id: str = Field(foreign_key="player.discord_id")
    issue_time: datetime = Field(default_factory=datetime.now)
    duration: timedelta = Field(default=timedelta(days=30))
    valid: bool = Field(default=True)

class Whitelist(WhitelistBase, table=True):
    pass

class WhitelistBan(WhitelistBase, table=True):
    duration: timedelta = Field(default=timedelta(days=14))
    reason: str | None = Field()

class Auth(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    token_hash: str = Field(unique=True, index=True)
