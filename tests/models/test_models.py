from app.database.models import Player
from sqlmodel import Session


class TestCreateEntry:
    def test_create_player(
        self,
        db_session: Session,
        discord_id: str,
        ckey: str,
    ) -> None:
        player = Player(discord_id=discord_id, ckey=ckey)
        db_session.add(player)
        db_session.commit()
        db_session.refresh(player)

        assert player.discord_id == discord_id
        assert player.ckey == ckey
