from datetime import datetime

from app.database.models import BanBase, BanType, Player
from pydantic import BaseModel


# region Get
class BanNested(BanBase):
    player: Player
    admin: Player


# endregion


# region Patch
class BanUpdate(BaseModel):
    admin_id: int
    """The admin who is updating the ban."""


class BanUpdateDetails(BanUpdate):
    """Handled in update_ban_by_id."""

    reason: str | None = None
    expiration_time: datetime | None = None
    ban_targets: dict[BanType, str] | None = None


class BanUpdateUnban(BanUpdate):
    reason: str | None = None


# endregion
