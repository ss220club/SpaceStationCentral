import uuid
from sqlmodel import Field, SQLModel

class Player(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

class Discord(SQLModel, table=True):
    player_id: uuid.UUID = Field(foreign_key="player.id", primary_key=True)
    discord_id: int = Field(unique=True)

class BYONDCkey(SQLModel, table=True):
    player_id: uuid.UUID = Field(foreign_key="player.id", primary_key=True)
    ckey: str = Field(unique=True)

class WizardsID(SQLModel, table=True):
    player_id: uuid.UUID = Field(foreign_key="player.id", primary_key=True)
    wiz_id: str = Field(unique=True)
