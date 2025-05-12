from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.models import Player


# region: GET
async def get_player(db: AsyncSession, player_id: int) -> Player:
    """
    Get player by id.

    Raises:
        HTTPException(404) - Player not found

    """
    player = await db.get(Player, player_id)
    if player is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")
    return player


async def get_player_by_discord_id(db: AsyncSession, discord_id: str) -> Player:
    """
    Get player by discord id.

    Raises:
        HTTPException(404) - Player not found

    """
    player = await db.get(Player, discord_id)
    if player is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")
    return player


async def get_player_by_ckey(db: AsyncSession, ckey: str) -> Player:
    """
    Get player by ckey.

    Raises:
        HTTPException(404) - Player not found

    """
    player = await db.get(Player, ckey)
    if player is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")
    return player


# endregion
