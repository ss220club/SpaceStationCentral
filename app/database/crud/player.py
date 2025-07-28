from fastapi import status
from fastapi.exceptions import HTTPException
from sqlmodel import select

from app.database.models import Player
from app.deps import SessionDep


# region: GET
def get_player_by_id(db: SessionDep, player_id: int) -> Player:
    """Get player by id."""
    player = db.get(Player, player_id)
    if player is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")

    return player


def get_player_by_discord_id(db: SessionDep, discord_id: str) -> Player:
    """Get player by discord id."""
    player = (db.exec(select(Player).where(Player.discord_id == discord_id))).first()
    if player is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")

    return player


def get_player_by_ckey(db: SessionDep, ckey: str) -> Player:
    """Get player by ckey."""
    player = (db.exec(select(Player).where(Player.ckey == ckey))).first()
    if player is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")

    return player


# endregion
