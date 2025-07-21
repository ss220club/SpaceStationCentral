import logging
from collections.abc import Sequence

from fastapi import HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.crud.player import get_player
from app.database.models import Ban, BanHistory, BanHistoryAction
from app.schemas.v2.ban import BanUpdateDetails, BanUpdateUnban


logger = logging.getLogger(__name__)


# region: GET


async def get_ban(db: AsyncSession, ban_id: int) -> Ban:
    """
    Get ban by id

    Raises:
        HTTPException(404) - Ban not found
    """
    ban = await db.get(Ban, ban_id)
    if ban is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ban not found")
    return ban


async def get_bans_by_player_discord_id(db: AsyncSession, discord_id: str) -> Sequence[Ban]:
    selection = select(Ban).where(Ban.player.discord_id == discord_id)
    return (await db.exec(selection)).all()


async def get_bans_by_player_ckey(db: AsyncSession, ckey: str) -> Sequence[Ban]:
    selection = select(Ban).where(Ban.player.ckey == ckey)
    return (await db.exec(selection)).all()


async def get_ban_history(db: AsyncSession, ban_id: int) -> Sequence[BanHistory]:
    selection = select(BanHistory).where(BanHistory.ban_id == ban_id)
    return (await db.exec(selection)).all()


# endregion


# region: POST
async def create_ban(db: AsyncSession, ban: Ban) -> Ban:
    # TODO: send redis event to publish the ban in discord
    db.add(ban)
    await db.commit()
    logger.info("Created ban: %s", ban)
    await db.refresh(ban)
    history = BanHistory(ban_id=ban.id, admin_id=ban.admin_id, action=BanHistoryAction.CREATE, details=ban.reason)  # pyright: ignore[reportArgumentType]
    db.add(history)
    await db.commit()
    logger.debug("Created ban history: %s", history)
    return ban


# endregion

# region: PATCH


async def update_ban(db: AsyncSession, ban_id: int, update: BanUpdateDetails) -> Ban:
    ban = await get_ban(db, ban_id)
    update_author = await get_player(db, update.update_author_id)
    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(ban, key, value)
    db.add(ban)
    await db.commit()
    logger.info("Updated ban: %s", ban)
    await db.refresh(ban)
    history = BanHistory(
        ban_id=ban.id,  # pyright: ignore[reportArgumentType]
        admin_id=update_author.id,  # pyright: ignore[reportArgumentType]
        action=BanHistoryAction.UPDATE,
        details=update.model_dump_json(),
    )
    db.add(history)
    await db.commit()
    logger.debug("Created ban history: %s", history)
    return ban


async def unban(db: AsyncSession, ban_id: int, unban: BanUpdateUnban) -> Ban:
    ban = await get_ban(db, ban_id)
    update_author = await get_player(db, unban.update_author_id)
    ban.valid = False
    db.add(ban)
    await db.commit()
    logger.info("Updated ban: %s", ban)
    history = BanHistory(
        ban_id=ban.id,  # pyright: ignore[reportArgumentType]
        admin_id=update_author.id,  # pyright: ignore[reportArgumentType]
        action=BanHistoryAction.UNBAN,
        details=unban.reason,
    )
    db.add(history)
    await db.commit()
    logger.debug("Created ban history: %s", history)
    return ban


# endregion
