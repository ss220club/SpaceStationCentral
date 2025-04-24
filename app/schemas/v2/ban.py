from datetime import datetime

from app.database.models import BanBase, Player
from pydantic import BaseModel


# region Get
class BanNested(BanBase):
    player: Player
    admin: Player


# endregion

# region Patch


class BanUpdate(BaseModel):
    reason: str | None = None
    expiration_time: datetime | None = None
    valid: bool | None = None


# endregion
