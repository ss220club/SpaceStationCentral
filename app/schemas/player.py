from pydantic import BaseModel


class PlayerPatch(BaseModel):
    discord_id: str | None = None
    ckey: str | None = None

class NewPlayer(BaseModel):
    discord_id: str
    ckey: str | None = None