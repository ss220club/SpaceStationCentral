from sqlmodel import Session, select

from app.core.exceptions import EntityNotFoundError
from app.database.models import Player


# region: GET
def get_player_by_id(db: Session, player_id: int) -> Player:
    """Get player by id."""
    player = db.get(Player, player_id)
    if player is None:
        raise EntityNotFoundError("Player not found")

    return player


def get_player_by_discord_id(db: Session, discord_id: str) -> Player:
    """Get player by discord id."""
    player = (db.exec(select(Player).where(Player.discord_id == discord_id))).first()
    if player is None:
        raise EntityNotFoundError("Player not found")

    return player


def get_player_by_ckey(db: Session, ckey: str) -> Player:
    """Get player by ckey."""
    player = (db.exec(select(Player).where(Player.ckey == ckey))).first()
    if player is None:
        raise EntityNotFoundError("Player not found")

    return player


# endregion
# region: POST
def create_player(db: Session, discord_id: str, ckey: str) -> Player:
    player = Player(discord_id=discord_id, ckey=ckey)
    db.add(player)
    db.commit()
    db.refresh(player)
    return player


# endregion
