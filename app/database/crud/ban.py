import logging

from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.models import Ban, BanHistory, BanHistoryAction
from app.schemas.v2.ban import BanUpdate


logger = logging.getLogger(__name__)


async def create_ban(db: AsyncSession, ban: Ban) -> Ban:
    db.add(ban)
    await db.commit()
    logger.info("Created ban: %s", ban)
    await db.refresh(ban)
    history = BanHistory(ban_id=ban.id, admin_id=ban.admin_id, action=BanHistoryAction.CREATE, details=ban.reason)  # pyright: ignore[reportArgumentType]
    db.add(history)
    await db.commit()
    logger.debug("Created ban history: %s", history)
    return ban


async def update_ban(db: AsyncSession, ban_id: int, update: BanUpdate) -> Ban:
    ban = await db.get(Ban, ban_id)
    if ban is None:
        raise ValueError("Ban not found")
    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(ban, key, value)
    db.add(ban)
    await db.commit()
    logger.info("Updated ban: %s", ban)
    await db.refresh(ban)
    history = BanHistory(
        ban_id=ban.id,  # pyright: ignore[reportArgumentType]
        admin_id=ban.admin_id,
        action=BanHistoryAction.UPDATE,
        details=update.model_dump_json(),
    )
    db.add(history)
    await db.commit()
    logger.debug("Created ban history: %s", history)
    return ban
