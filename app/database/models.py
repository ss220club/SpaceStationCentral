from sqlmodel import Field, SQLModel

class Player(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    discord_id: str = Field(unique=True)
    ckey: str = Field(unique=True)
