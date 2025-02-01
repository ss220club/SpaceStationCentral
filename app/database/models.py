from datetime import datetime, timedelta
from secrets import token_urlsafe

from sqlmodel import Field, SQLModel

DEFAULT_WHITELIST_EXPIRATION_TIME = timedelta(days=30)
DEFAULT_WHITELIST_BAN_EXPIRATION_TIME = timedelta(days=14)

DEFAULT_TOKEN_LEN = 32
DEFAULT_TOKEN_EXPIRATION_TIME = timedelta(minutes=5)


class Player(SQLModel, table=True):
    __tablename__ = "player"
    id: int = Field(default=None, primary_key=True)
    # Actually is a pretty big int. Is way **too** big for a lot of software to handle
    discord_id: str = Field(max_length=32, unique=True, index=True)
    ckey: str | None = Field(max_length=32, unique=True, index=True)
    # wizards_id: str | None = Field(unique=True, index=True) # Most likely is some kind of uuid


class CkeyLinkToken(SQLModel, table=True):
    __tablename__ = "ckey_link_token"
    id: int = Field(default=None, primary_key=True)
    ckey: str = Field(max_length=32, unique=True, index=True)
    token: str = Field(
        max_length=64, unique=True, default_factory=lambda: token_urlsafe(DEFAULT_TOKEN_LEN), index=True)
    expiration_time: datetime = Field(
        default_factory=lambda: datetime.now() + DEFAULT_TOKEN_EXPIRATION_TIME)


class WhitelistBase(SQLModel):
    id: int = Field(default=None, primary_key=True)
    player_id: int = Field(foreign_key="player.id", index=True)
    wl_type: str = Field(max_length=32, default="default")
    admin_id: int = Field(foreign_key="player.id")
    issue_time: datetime = Field(default_factory=datetime.now)
    expiration_time: datetime = Field(
        default_factory=lambda: datetime.now() + DEFAULT_WHITELIST_EXPIRATION_TIME)
    valid: bool = Field(default=True)


class Whitelist(WhitelistBase, table=True):
    __tablename__ = "whitelist"


class WhitelistBan(WhitelistBase, table=True):
    __tablename__ = "whitelist_ban"
    expiration_time: datetime = Field(
        default_factory=lambda: datetime.now() + DEFAULT_WHITELIST_BAN_EXPIRATION_TIME)
    reason: str | None = Field(max_length=1024)


class Auth(SQLModel, table=True):
    __tablename__ = "auth"
    id: int = Field(default=None, primary_key=True)
    token_hash: str = Field(max_length=64, unique=True, index=True)


class Donation(SQLModel, table=True):
    __tablename__ = "donation"
    id: int = Field(default=None, primary_key=True)
    player_id: int = Field(foreign_key="player.id", index=True)
    amount: int = Field()
    date: datetime = Field(default_factory=datetime.now)
