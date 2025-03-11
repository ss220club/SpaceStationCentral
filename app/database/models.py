from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe

from sqlmodel import Field, SQLModel


DEFAULT_WHITELIST_EXPIRATION_TIME = timedelta(days=30)
DEFAULT_WHITELIST_BAN_EXPIRATION_TIME = timedelta(days=14)
DEFAULT_DONATION_EXPIRATION_TIME = timedelta(days=30)

DEFAULT_TOKEN_LEN = 32
DEFAULT_TOKEN_EXPIRATION_TIME = timedelta(minutes=5)


class Player(SQLModel, table=True):
    __tablename__ = "player"  # type: ignore
    id: int | None = Field(default=None, primary_key=True)
    discord_id: str = Field(max_length=32, unique=True, index=True)
    """
    Actually is a pretty big int. Is way **too** big for a lot of software to handle
    """
    ckey: str | None = Field(max_length=32, unique=True, index=True)
    # wizards_id: str | None = Field(unique=True, index=True) # Most likely is some kind of uuid


class CkeyLinkToken(SQLModel, table=True):
    __tablename__ = "ckey_link_token"  # type: ignore
    id: int | None = Field(default=None, primary_key=True)
    ckey: str = Field(max_length=32, unique=True, index=True)
    token: str = Field(max_length=64, unique=True, default_factory=lambda: token_urlsafe(DEFAULT_TOKEN_LEN), index=True)
    expiration_time: datetime = Field(default_factory=lambda: datetime.now(UTC) + DEFAULT_TOKEN_EXPIRATION_TIME)


class WhitelistBase(SQLModel):
    id: int | None = Field(default=None, primary_key=True)
    player_id: int = Field(foreign_key="player.id", index=True)
    server_type: str = Field(max_length=32, index=True, default="default")
    admin_id: int = Field(foreign_key="player.id")
    issue_time: datetime = Field(default_factory=datetime.now)
    expiration_time: datetime = Field(default_factory=lambda: datetime.now(UTC) + DEFAULT_WHITELIST_EXPIRATION_TIME)
    valid: bool = Field(default=True, index=True)


class Whitelist(WhitelistBase, table=True):
    __tablename__ = "whitelist"  # type: ignore


class WhitelistBan(WhitelistBase, table=True):
    __tablename__ = "whitelist_ban"  # type: ignore
    expiration_time: datetime = Field(default_factory=lambda: datetime.now(UTC) + DEFAULT_WHITELIST_BAN_EXPIRATION_TIME)
    reason: str | None = Field(max_length=1024)


class APIAuth(SQLModel, table=True):
    __tablename__ = "api_auth"  # type: ignore
    id: int | None = Field(default=None, primary_key=True)
    token_hash: str = Field(max_length=64, unique=True, index=True)


class Donation(SQLModel, table=True):
    __tablename__ = "donation"  # type: ignore
    id: int | None = Field(default=None, primary_key=True)
    player_id: int = Field(foreign_key="player.id", index=True)
    tier: int = Field()
    issue_time: datetime = Field(default_factory=datetime.now)
    expiration_time: datetime = Field(default_factory=lambda: datetime.now(UTC) + DEFAULT_DONATION_EXPIRATION_TIME)
    valid: bool = Field(default=True)
