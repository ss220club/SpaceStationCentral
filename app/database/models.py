import uuid
from sqlalchemy import BigInteger, Column, Integer
from sqlmodel import Field, Relationship, SQLModel

class CkeyToDiscord(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    ckey: str = Field(default=None, index=True)
    discord_id: str = Field(default=None, index=True) # Discord id is too big for an int
