import re
from datetime import datetime, timedelta
from secrets import token_urlsafe
from typing import Unpack

from pydantic import ConfigDict
from sqlmodel import Field, Relationship, SQLModel

from app.core.utils import utcnow2


DEFAULT_WHITELIST_EXPIRATION_TIME = timedelta(days=30)
DEFAULT_WHITELIST_BAN_EXPIRATION_TIME = timedelta(days=14)
DEFAULT_DONATION_EXPIRATION_TIME = timedelta(days=30)

DEFAULT_TOKEN_LEN = 32
DEFAULT_TOKEN_EXPIRATION_TIME = timedelta(minutes=5)


class BaseSqlModel(SQLModel):
    def __init_subclass__(cls, **kwargs: Unpack[ConfigDict]) -> None:
        """Automatically set the table name to the class name in snake_case."""
        super().__init_subclass__(**kwargs)
        table_name = re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()
        cls.__tablename__: str = table_name  # pyright: ignore[reportIncompatibleVariableOverride]


# *Base models exist to create database and pydantic models based on them separately
# which allows to embed relationships into model dumps


class PlayerBase(BaseSqlModel):
    id: int | None = Field(default=None, primary_key=True)
    discord_id: str = Field(max_length=32, unique=True, index=True)
    """
    Actually is a pretty big int. Is way **too** big for a lot of software to handle
    """
    ckey: str | None = Field(default=None, max_length=32, unique=True, index=True)
    # wizards_id: str | None = Field(unique=True, index=True) # Most likely is some kind of uuid


class Player(PlayerBase, table=True):
    whitelists: list["Whitelist"] = Relationship(
        back_populates="player", sa_relationship_kwargs={"foreign_keys": "Whitelist.player_id"}
    )
    whitelists_issued: list["Whitelist"] = Relationship(
        back_populates="admin", sa_relationship_kwargs={"foreign_keys": "Whitelist.admin_id"}
    )

    whitelist_bans: list["WhitelistBan"] = Relationship(
        back_populates="player", sa_relationship_kwargs={"foreign_keys": "WhitelistBan.player_id"}
    )
    whitelist_bans_issued: list["WhitelistBan"] = Relationship(
        back_populates="admin", sa_relationship_kwargs={"foreign_keys": "WhitelistBan.admin_id"}
    )

    donations: list["Donation"] = Relationship(back_populates="player")


class CkeyLinkToken(BaseSqlModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    ckey: str = Field(max_length=32, unique=True, index=True)
    token: str = Field(max_length=64, unique=True, default_factory=lambda: token_urlsafe(DEFAULT_TOKEN_LEN), index=True)
    expiration_time: datetime = Field(
        default_factory=lambda: utcnow2() + DEFAULT_TOKEN_EXPIRATION_TIME,
    )


class WhitelistBase(BaseSqlModel):
    id: int | None = Field(default=None, primary_key=True)
    player_id: int = Field(foreign_key="player.id", index=True)
    server_type: str = Field(max_length=32, index=True, default="default")
    admin_id: int = Field(foreign_key="player.id")
    issue_time: datetime = Field(default_factory=datetime.now)
    expiration_time: datetime = Field(
        default_factory=lambda: utcnow2() + DEFAULT_WHITELIST_EXPIRATION_TIME,
    )
    valid: bool = Field(default=True, index=True)


class Whitelist(WhitelistBase, table=True):
    player: Player = Relationship(
        back_populates="whitelists", sa_relationship_kwargs={"foreign_keys": "Whitelist.player_id"}
    )
    admin: Player = Relationship(
        back_populates="whitelists_issued",
        sa_relationship_kwargs={"foreign_keys": "Whitelist.admin_id"},
    )


class WhitelistBanBase(WhitelistBase):
    expiration_time: datetime = Field(
        default_factory=lambda: utcnow2() + DEFAULT_WHITELIST_BAN_EXPIRATION_TIME,
    )
    reason: str | None = Field(max_length=1024, default=None)


class WhitelistBan(WhitelistBanBase, table=True):
    player: Player = Relationship(
        back_populates="whitelist_bans",
        sa_relationship_kwargs={"foreign_keys": "WhitelistBan.player_id"},
    )
    admin: Player = Relationship(
        back_populates="whitelist_bans_issued",
        sa_relationship_kwargs={"foreign_keys": "WhitelistBan.admin_id"},
    )


class ApiAuth(BaseSqlModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    token_hash: str = Field(max_length=64, unique=True, index=True)


class DonationBase(BaseSqlModel):
    id: int | None = Field(default=None, primary_key=True)
    player_id: int = Field(foreign_key="player.id", index=True)
    tier: int = Field()
    issue_time: datetime = Field(default_factory=datetime.now)
    expiration_time: datetime = Field(
        default_factory=lambda: utcnow2() + DEFAULT_DONATION_EXPIRATION_TIME,
    )
    valid: bool = Field(default=True)


class Donation(DonationBase, table=True):
    player: Player = Relationship(back_populates="donations")
