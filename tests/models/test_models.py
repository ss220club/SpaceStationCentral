from app.database.crud.player import create_player
from sqlmodel import Session


class TestDBMetadata:
    def test_init_db(self, db_session: Session) -> None:
        assert db_session


class TestCreateEntry:
    """
    Test that models and relations are correct by creating instances.
    """

    def test_create_player(
        self,
        db_session: Session,
        discord_id: str,
        ckey: str,
    ) -> None:
        player = create_player(db_session, discord_id, ckey)

        assert player.discord_id == discord_id
        assert player.ckey == ckey
