from sqlmodel import Session

from tests.conftest import create_player


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
        player = create_player(db_session, ckey, discord_id)

        assert player.discord_id == discord_id
        assert player.ckey == ckey
