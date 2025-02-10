from pydantic import BaseModel


class PlayerPatch(BaseModel):
    ckey: str | None = None
    discord_id: str | None = None
