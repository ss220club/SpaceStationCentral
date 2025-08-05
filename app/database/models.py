import enum
import re
from datetime import datetime, timedelta
from secrets import token_urlsafe
from typing import Unpack

from pydantic import ConfigDict
from sqlmodel import Field, Relationship, SQLModel

from app.core.utils import utcnow2


# region Constants

DEFAULT_WHITELIST_EXPIRATION_TIME = timedelta(days=30)
DEFAULT_WHITELIST_BAN_EXPIRATION_TIME = timedelta(days=14)
DEFAULT_DONATION_EXPIRATION_TIME = timedelta(days=30)
DEFAULT_TOKEN_LEN = 32
DEFAULT_TOKEN_EXPIRATION_TIME = timedelta(minutes=5)
MAX_REASON_LENGTH = 2048
MAX_HISTORY_DETAILS_LEN = MAX_REASON_LENGTH * 2


class NoteKind(enum.Enum):
    NOTE = "NOTE"
    WATCHLIST = "WATCHLIST"


class NoteSeverity(enum.Enum):
    POSITIVE = "POSITIVE"
    INFO = "INFO"
    MINOR = "MINOR"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class BanHistoryAction(enum.Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    INVALIDATE = "INVALIDATE"


# endregion
# region Models


class BaseSqlModel(SQLModel):
    def __init_subclass__(cls, **kwargs: Unpack[ConfigDict]) -> None:
        super().__init_subclass__(**kwargs)
        if kwargs.get("table"):
            table_name = re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()
            cls.__tablename__: str = table_name  # pyright: ignore[reportIncompatibleVariableOverride]


class PlayerBase(BaseSqlModel):
    id: int | None = Field(default=None, primary_key=True)
    discord_id: str = Field(max_length=32, unique=True, index=True)
    ckey: str | None = Field(default=None, max_length=32, unique=True, index=True)


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
    bans: list["Ban"] = Relationship(back_populates="player", sa_relationship_kwargs={"foreign_keys": "Ban.player_id"})
    bans_issued: list["Ban"] = Relationship(
        back_populates="admin", sa_relationship_kwargs={"foreign_keys": "Ban.admin_id"}
    )
    bans_edited: list["BanHistory"] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "and_(BanHistory.admin_id == Player.id, "
            + f"BanHistory.action != '{BanHistoryAction.CREATE.name}')",
            # Could be a sqlite thing, but somewhy db stores the enum entry name
            "viewonly": True,
        }
    )
    notes: list["Note"] = Relationship(
        back_populates="player", sa_relationship_kwargs={"foreign_keys": "Note.player_id"}
    )
    notes_issued: list["Note"] = Relationship(
        back_populates="admin", sa_relationship_kwargs={"foreign_keys": "Note.admin_id"}
    )


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
        back_populates="whitelists", sa_relationship_kwargs={"foreign_keys": "[Whitelist.player_id]"}
    )
    admin: Player = Relationship(
        back_populates="whitelists_issued", sa_relationship_kwargs={"foreign_keys": "[Whitelist.admin_id]"}
    )


class WhitelistBanBase(WhitelistBase):
    expiration_time: datetime = Field(
        default_factory=lambda: utcnow2() + DEFAULT_WHITELIST_BAN_EXPIRATION_TIME,
    )
    reason: str | None = Field(max_length=MAX_REASON_LENGTH, default=None)


class WhitelistBan(WhitelistBanBase, table=True):
    player: Player = Relationship(
        back_populates="whitelist_bans", sa_relationship_kwargs={"foreign_keys": "[WhitelistBan.player_id]"}
    )
    admin: Player = Relationship(
        back_populates="whitelist_bans_issued", sa_relationship_kwargs={"foreign_keys": "[WhitelistBan.admin_id]"}
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


class BanBase(BaseSqlModel):
    id: int | None = Field(default=None, primary_key=True)
    player_id: int = Field(foreign_key="player.id", index=True)
    admin_id: int = Field(foreign_key="player.id")
    issue_time: datetime = Field(default_factory=datetime.now)
    expiration_time: datetime = Field()
    reason: str | None = Field(max_length=MAX_REASON_LENGTH, default=None)
    valid: bool = Field(default=True)


class Ban(BanBase, table=True):
    player: Player = Relationship(back_populates="bans", sa_relationship_kwargs={"foreign_keys": "[Ban.player_id]"})
    admin: Player = Relationship(
        back_populates="bans_issued", sa_relationship_kwargs={"foreign_keys": "[Ban.admin_id]"}
    )
    ban_targets: list["BanTarget"] = Relationship(back_populates="ban")
    history: list["BanHistory"] = Relationship(back_populates="ban")


class BanType(enum.Enum):
    GAME = "game"
    SERVER = "server"
    JOB = "job"


class BanTargetBase(BaseSqlModel):
    id: int | None = Field(default=None, primary_key=True)
    ban_id: int = Field(foreign_key="ban.id", index=True)
    target_type: BanType = Field(default=BanType.GAME, index=True)
    target: str = Field(max_length=32, unique=True, index=True)


class BanTarget(BanTargetBase, table=True):
    ban: Ban = Relationship(back_populates="ban_targets")


class NoteBase(BaseSqlModel):
    id: int | None = Field(default=None, primary_key=True)
    player_id: int = Field(foreign_key="player.id", index=True)
    admin_id: int = Field(foreign_key="player.id")
    issue_time: datetime = Field(default_factory=datetime.now)
    content: str = Field(max_length=MAX_REASON_LENGTH)
    kind: NoteKind = Field(default=NoteKind.NOTE)
    severity: NoteSeverity = Field(default=NoteSeverity.INFO)
    is_secret: bool = Field(default=True)
    valid: bool = Field(default=True)


class Note(NoteBase, table=True):
    player: Player = Relationship(back_populates="notes", sa_relationship_kwargs={"foreign_keys": "[Note.player_id]"})
    admin: Player = Relationship(
        back_populates="notes_issued", sa_relationship_kwargs={"foreign_keys": "[Note.admin_id]"}
    )


class BanHistoryBase(BaseSqlModel):
    id: int | None = Field(default=None, primary_key=True)
    ban_id: int = Field(foreign_key="ban.id", index=True)
    admin_id: int = Field(foreign_key="player.id")
    action: BanHistoryAction = Field(default=BanHistoryAction.CREATE)
    details: str | None = Field(max_length=MAX_HISTORY_DETAILS_LEN, default=None)
    timestamp: datetime = Field(default_factory=datetime.now)


class BanHistory(BanHistoryBase, table=True):
    ban: Ban = Relationship(back_populates="history")
    admin: Player = Relationship()


# endregion
