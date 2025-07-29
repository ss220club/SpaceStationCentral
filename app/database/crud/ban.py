import logging
from collections.abc import Sequence

from sqlmodel import Session, select

from app.core.exceptions import EntityNotFoundError
from app.database.crud.player import get_player_by_id
from app.database.models import Ban, BanHistory, BanHistoryAction
from app.schemas.v2.ban import BanUpdateDetails, BanUpdateUnban


logger = logging.getLogger(__name__)


# region: GET


def get_ban(db: Session, ban_id: int) -> Ban:
    """Get ban by id."""
    ban = db.get(Ban, ban_id)
    if ban is None:
        raise EntityNotFoundError("Ban not found")
    return ban


def get_bans_by_player_discord_id(db: Session, discord_id: str) -> Sequence[Ban]:
    selection = select(Ban).where(Ban.player.discord_id == discord_id)
    return (db.exec(selection)).all()


def get_bans_by_player_ckey(db: Session, ckey: str) -> Sequence[Ban]:
    selection = select(Ban).where(Ban.player.ckey == ckey)
    return (db.exec(selection)).all()


def get_ban_history(db: Session, ban_id: int) -> Sequence[BanHistory]:
    selection = select(BanHistory).where(BanHistory.ban_id == ban_id)
    return (db.exec(selection)).all()


# endregion


# region: POST
def create_ban(db: Session, ban: Ban) -> Ban:
    # TODO: send redis event to publish the ban in discord
    db.add(ban)
    db.flush()
    db.refresh(ban)
    logger.info("Created ban: %s", ban)
    history = BanHistory(ban_id=ban.id, admin_id=ban.admin_id, action=BanHistoryAction.CREATE, details=ban.reason)  # pyright: ignore[reportArgumentType]
    db.add(history)
    db.commit()
    db.refresh(history)
    logger.debug("Created initial ban history: %s", history)
    return ban


# endregion

# region: PATCH


def update_ban(db: Session, ban_id: int, update: BanUpdateDetails) -> Ban:
    ban = get_ban(db, ban_id)
    update_author = get_player_by_id(db, update.update_author_id)
    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(ban, key, value)
    db.add(ban)
    db.commit()
    logger.info("Updated ban: %s", ban)
    db.refresh(ban)
    history = BanHistory(
        ban_id=ban.id,  # pyright: ignore[reportArgumentType]
        admin_id=update_author.id,  # pyright: ignore[reportArgumentType]
        action=BanHistoryAction.UPDATE,
        details=update.model_dump_json(),
    )
    db.add(history)
    db.commit()
    logger.debug("Created ban history: %s", history)
    return ban


def unban(db: Session, ban_id: int, unban: BanUpdateUnban) -> Ban:
    ban = get_ban(db, ban_id)
    update_author = get_player_by_id(db, unban.update_author_id)
    ban.valid = False
    db.add(ban)
    db.commit()
    logger.info("Updated ban: %s", ban)
    history = BanHistory(
        ban_id=ban.id,  # pyright: ignore[reportArgumentType]
        admin_id=update_author.id,  # pyright: ignore[reportArgumentType]
        action=BanHistoryAction.INVALIDATE,
        details=unban.reason,
    )
    db.add(history)
    db.commit()
    logger.debug("Created ban history: %s", history)
    return ban


# endregion
