import logging

from sqlmodel import Session

from app.database.models import Ban, BanHistory, BanHistoryAction
from app.schemas.v2.ban import BanUpdate


logger = logging.getLogger(__name__)


def create_ban(db: Session, ban: Ban) -> Ban:
    db.add(ban)
    db.commit()
    logger.info("Created ban: %s", ban)
    db.refresh(ban)
    history = BanHistory(ban_id=ban.id, admin_id=ban.admin_id, action=BanHistoryAction.CREATE, details=ban.reason)  # pyright: ignore[reportArgumentType]
    db.add(history)
    db.commit()
    logger.debug("Created ban history: %s", history)
    return ban


def update_ban(db: Session, ban_id: int, update: BanUpdate) -> Ban:
    ban = db.get(Ban, ban_id)
    if ban is None:
        raise ValueError("Ban not found")
    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(ban, key, value)
    db.add(ban)
    db.commit()
    logger.info("Updated ban: %s", ban)
    db.refresh(ban)
    history = BanHistory(
        ban_id=ban.id,  # pyright: ignore[reportArgumentType]
        admin_id=ban.admin_id,
        action=BanHistoryAction.UPDATE,
        details=update.model_dump_json(),
    )
    db.add(history)
    db.commit()
    logger.debug("Created ban history: %s", history)
    return ban
