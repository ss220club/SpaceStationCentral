from datetime import datetime, timedelta
from secrets import token_urlsafe

from sqlmodel import Field, SQLModel

DEFAULT_WHITELIST_EXPIRATION_TIME = timedelta(days=30)
DEFAULT_WHITELIST_BAN_EXPIRATION_TIME = timedelta(days=14)

DEFAULT_TOKEN_LEN = 32
DEFAULT_TOKEN_EXPIRATION_TIME = timedelta(minutes=5)


class Player(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    # Actually is a pretty big int. Is way **too** big for a lot of software to handle
    discord_id: str = Field(unique=True, index=True)
    ckey: str | None = Field(unique=True, index=True)
    # wizards_id: str | None = Field(unique=True, index=True) # Most likely is some kind of uuid


class CkeyLinkToken(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    ckey: str = Field(unique=True, index=True)
    token: str = Field(
        unique=True, default_factory=lambda: token_urlsafe(DEFAULT_TOKEN_LEN), index=True)
    expiration_time: datetime = Field(
        default_factory=lambda: datetime.now() + DEFAULT_TOKEN_EXPIRATION_TIME)


class WhitelistBase(SQLModel):
    id: int = Field(default=None, primary_key=True)
    player_id: str = Field(foreign_key="player.id", index=True)
    wl_type: str = Field(default="default")
    admin_id: str = Field(foreign_key="player.id")
    issue_time: datetime = Field(default_factory=datetime.now)
    expiration_time: datetime = Field(
        default_factory=lambda: datetime.now() + DEFAULT_WHITELIST_EXPIRATION_TIME)
    valid: bool = Field(default=True)


class Whitelist(WhitelistBase, table=True):
    pass


class WhitelistBan(WhitelistBase, table=True):
    expiration_time: datetime = Field(
        default_factory=lambda: datetime.now() + DEFAULT_WHITELIST_BAN_EXPIRATION_TIME)
    reason: str | None = Field()


class Auth(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    token_hash: str = Field(unique=True, index=True)


class Donation(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    player_id: str = Field(foreign_key="player.id", index=True)
    amount: int = Field()
    date: datetime = Field(default_factory=datetime.now)
