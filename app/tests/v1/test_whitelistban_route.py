import datetime

from app.database.models import Whitelist
from app.schemas.whitelist import NewWhitelistBanDiscord, NewWhitelistBanCkey, NewWhitelistCkey


def test_create_whitelistban_by_discord(client, player_factory, wl_type, duration_days, bearer):
    player = player_factory()
    admin = player_factory()
    wl = NewWhitelistBanDiscord(
        player_discord_id=player.discord_id,
        admin_discord_id=admin.discord_id,
        duration_days=duration_days,
        reason="test"
    )
    response = client.post(f"whitelistban/{wl_type}/discord",
                           json=wl.model_dump(),
                           headers={"Authorization": f"Bearer {bearer}"})
    assert response.status_code == 201

    wl = Whitelist.model_validate(response.json())

    assert wl.player_id == player.id
    assert wl.admin_id == admin.id
    assert wl.wl_type == wl_type
    assert wl.expiration_time > datetime.datetime.now()
    assert wl.valid


def test_create_whitelistban_by_ckey(client, player_factory, wl_type, duration_days, bearer):
    player = player_factory()
    admin = player_factory()
    wlban = NewWhitelistBanCkey(
        player_ckey=player.ckey,
        admin_ckey=admin.ckey,
        duration_days=duration_days,
        reason="test"
    )
    response = client.post(f"whitelistban/{wl_type}/ckey",
                           json=wlban.model_dump(),
                           headers={"Authorization": f"Bearer {bearer}"})
    assert response.status_code == 201

    wlban = Whitelist.model_validate(response.json())

    assert wlban.player_id == player.id
    assert wlban.admin_id == admin.id
    assert wlban.wl_type == wl_type
    assert wlban.expiration_time > datetime.datetime.now()
    assert wlban.valid


def test_ban_prevents_whitelist(client, player_factory, wl_type, duration_days, bearer):
    player = player_factory()
    admin = player_factory()
    wlban = NewWhitelistBanCkey(
        player_ckey=player.ckey,
        admin_ckey=admin.ckey,
        duration_days=duration_days,
        reason="test"
    )
    response = client.post(f"whitelistban/{wl_type}/ckey",
                           json=wlban.model_dump(),
                           headers={"Authorization": f"Bearer {bearer}"})
    assert response.status_code == 201

    wl = NewWhitelistCkey(
        player_ckey=player.ckey,
        admin_ckey=admin.ckey,
        duration_days=duration_days
    )
    response = client.post(f"whitelist/{wl_type}/ckey",
                           json=wl.model_dump(),
                           headers={"Authorization": f"Bearer {bearer}"})
    assert response.status_code == 409
