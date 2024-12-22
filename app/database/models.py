from datetime import datetime, timedelta
from secrets import token_urlsafe
from sqlmodel import Field, SQLModel

class Player(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    discord_id: str = Field(unique=True, index=True)
    ckey: str = Field(unique=True, index=True)

class OneTimeToken(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    ckey: str = Field(unique=True, index=True)
    token: str = Field(unique=True, default_factory=lambda: token_urlsafe(32), index=True)
    expiry: datetime = Field(default_factory=lambda: datetime.now() + timedelta(minutes=5)) 

class Whitelist(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    player_id: int = Field(foreign_key="player.id", index=True)
    type: str
    admin_id: int = Field(foreign_key="player.id")
    issue_time: datetime = Field(default_factory=datetime.now)
    duration: timedelta = Field(default=timedelta(days=30))
    active: bool = Field(default=True)

class WhitelistBan(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    player_id: int = Field(foreign_key="player.id", index=True)
    type: str
    admin_id: int = Field(foreign_key="player.id")
    issue_time: datetime = Field(default_factory=datetime.now)
    duration: timedelta = Field(default=timedelta(days=14))
    active: bool = Field(default=True)
