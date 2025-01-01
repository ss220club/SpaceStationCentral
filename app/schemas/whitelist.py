from pydantic import BaseModel

class NewWhitelistCkey(BaseModel):
    player_ckey: str
    admin_ckey: str
    wl_type: str
    duration_in_days: int
