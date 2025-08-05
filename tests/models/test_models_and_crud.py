from app.database.crud.ban import create_ban, update_ban_by_id, update_ban_unban_by_id
from app.database.crud.player import create_player
from app.database.models import BanHistoryAction, BanType, Player
from app.schemas.v2.ban import BanUpdateDetails, BanUpdateUnban
from sqlmodel import Session


class TestDBMetadata:
    def test_init_db(self, db_session: Session) -> None:
        assert db_session


class TestCreateEntry:
    """
    Test that models and relations are correct by messing aroudn with instances.
    """

    def test_create_player(
        self,
        db_session: Session,
        discord_id: str,
        ckey: str,
    ) -> None:
        player = create_player(db_session, discord_id, ckey)

        assert player

    def test_create_ban(self, db_session: Session, player: Player) -> None:
        ban = create_ban(db_session, player, player, 1, "test", {BanType.GAME: "ss13"})

        assert len(player.bans) == 1
        assert len(player.bans_issued) == 1
        assert player.bans[0] == ban
        assert player.bans_issued[0] == ban

        assert ban.player == player
        assert ban.admin == player
        assert len(ban.ban_targets) == 1
        assert ban.ban_targets[0].target_type == BanType.GAME
        assert ban.ban_targets[0].target == "ss13"

        assert len(ban.history) == 1
        assert ban.history[0].action == BanHistoryAction.CREATE

    def test_update_ban(self, db_session: Session, player: Player) -> None:
        ban = create_ban(
            db_session, player, player, 1, "test", {BanType.GAME: "ss13"}
        )  # TODO: Move creating ban to conftest
        update = BanUpdateDetails(
            admin_id=player.id,  # pyright: ignore[reportArgumentType]
            reason="test",
            ban_targets={BanType.JOB: "janitor"},
        )
        update_ban_by_id(db_session, ban.id, update)  # pyright: ignore[reportArgumentType]

        assert len(player.bans_edited) == 1
        assert player.bans_edited[0].ban == ban

        assert len(ban.history) == 2  # First history entry is creation
        assert ban.history[1].action == BanHistoryAction.UPDATE
        assert ban.history[1].details == update.model_dump_json(exclude_unset=True)

    def test_update_ban_unban(self, db_session: Session, player: Player) -> None:
        ban = create_ban(db_session, player, player, 1, "test", {BanType.GAME: "ss13"})
        unban = BanUpdateUnban(admin_id=player.id, reason="test unban")  # pyright: ignore[reportArgumentType]
        update_ban_unban_by_id(db_session, ban.id, unban)  # pyright: ignore[reportArgumentType]

        assert len(ban.history) == 2  # First history entry is creation
        assert ban.history[1].action == BanHistoryAction.INVALIDATE
        assert ban.history[1].details == unban.reason
        assert not ban.valid
