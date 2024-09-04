import uuid
from sqlmodel import Field, SQLModel

class Player(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

class Discord(SQLModel, table=True):
    player_id: uuid.UUID = Field(foreign_key="player.id")
    discord_id: int

class BYONDCkey(SQLModel, table=True):
    player_id: uuid.UUID = Field(foreign_key="player.id")
    ckey: str

class WizardsID(SQLModel, table=True):
    player_id: uuid.UUID = Field(foreign_key="player.id")
    wiz_id: str
