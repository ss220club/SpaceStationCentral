from sqlmodel import select

from app.database.models import Player
from app.deps import SessionDep


# region: GET
def get_player_by_id(db: SessionDep, player_id: int) -> Player | None:
    """Get player by id."""
    return db.get(Player, player_id)


def get_player_by_discord_id(db: SessionDep, discord_id: str) -> Player | None:
    """Get player by discord id."""
    return (db.exec(select(Player).where(Player.discord_id == discord_id))).first()


def get_player_by_ckey(db: SessionDep, ckey: str) -> Player | None:
    """Get player by ckey."""
    return (db.exec(select(Player).where(Player.ckey == ckey))).first()


# endregion
