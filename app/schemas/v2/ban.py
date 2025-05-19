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
    update_author_id: int
    """The admin who is updating the ban"""


class BanUpdateDetails(BanUpdate):
    reason: str | None = None
    expiration_time: datetime | None = None


class BanUpdateUnban(BanUpdate):
    reason: str | None = None


# endregion
