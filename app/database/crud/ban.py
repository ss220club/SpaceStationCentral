import logging
from datetime import timedelta

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.core.exceptions import EntityNotFoundError
from app.core.utils import utcnow2
from app.database.crud.player import get_player_by_id
from app.database.models import Ban, BanHistory, BanHistoryAction, BanTarget, BanType, Player
from app.schemas.v2.ban import BanUpdateDetails, BanUpdateUnban


logger = logging.getLogger(__name__)


# region: GET


def get_ban_by_id(db: Session, ban_id: int) -> Ban:
    """Get ban by id."""
    ban = db.get(Ban, ban_id)
    if ban is None:
        raise EntityNotFoundError("Ban not found")
    return ban


# endregion


# region: POST
def create_ban(
    db: Session, player: Player, admin: Player, duration_days: int, reason: str, ban_targets: dict[BanType, str]
) -> Ban:
    ban = Ban(
        player=player,
        admin=admin,
        issue_time=utcnow2(),
        expiration_time=utcnow2() + timedelta(days=duration_days),
        reason=reason,
        valid=True,
        ban_targets=[BanTarget(ban_type=ban_type, target=target) for ban_type, target in ban_targets.items()],  # pyright: ignore[reportCallIssue] # It doesnt understand that we can pass by relation instead of id
    )
    db.add(ban)
    ban_history = BanHistory(  # pyright: ignore[reportCallIssue] # It doesnt understand that we can pass by relation instead of id
        ban=ban,
        admin=admin,
        action=BanHistoryAction.CREATE,
    )
    db.add(ban_history)
    db.commit()
    logger.info("Created ban: %s", ban)
    # TODO: redis event to send bans to discord
    # Could be handled at api level to use the correct schema with all the fields
    return ban


# endregion

# region: PATCH


def update_ban_by_id(db: Session, ban_id: int, update: BanUpdateDetails) -> Ban:
    ban = get_ban_by_id(db, ban_id)
    admin = get_player_by_id(db, update.admin_id)

    update_dict = update.model_dump(exclude_unset=True, exclude={"ban_targets"})
    for key, value in update_dict.items():
        setattr(ban, key, value)
    db.add(ban)

    ban_history = BanHistory(  # pyright: ignore[reportCallIssue] # It doesnt understand that we can pass by relation instead of id
        ban=ban,
        admin=admin,
        action=BanHistoryAction.UPDATE,
        details=update.model_dump_json(exclude_unset=True),
    )
    db.add(ban_history)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        logger.error("Update failed. Patch: %s. Error: %s", update, e)
        raise e
    db.refresh(ban)

    return ban


def update_ban_unban_by_id(db: Session, ban_id: int, unban: BanUpdateUnban) -> Ban:
    ban = get_ban_by_id(db, ban_id)
    admin = get_player_by_id(db, unban.admin_id)

    ban.valid = False
    db.add(ban)

    ban_history = BanHistory(  # pyright: ignore[reportCallIssue] # It doesnt understand that we can pass by relation instead of id
        ban=ban,
        admin=admin,
        action=BanHistoryAction.INVALIDATE,
        details=unban.reason,
    )
    db.add(ban_history)
    db.commit()
    db.refresh(ban)
    return ban


# endregion
