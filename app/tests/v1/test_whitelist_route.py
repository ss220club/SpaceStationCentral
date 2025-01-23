import datetime

from app.database.models import Whitelist
from app.schemas.whitelist import NewWhitelistDiscord, NewWhitelistCkey


def test_get_whitelists_general_empty(client):
    response = client.get("/whitelist/")
    assert response.status_code == 200
    assert len(response.json()) == 0


def test_get_whitelists_all(client, whitelist_factory):
    wls = [whitelist_factory() for _ in range(5)]
    response = client.get("/whitelist?active_only=false")
    assert response.status_code == 200
    assert len(response.json()) == len(wls)

    assert wls == [Whitelist.model_validate(wl) for wl in response.json()]


def test_get_whitelists_active(client, whitelist_factory):
    wls = [whitelist_factory() for _ in range(5)]
    active_wls = [wl for wl in wls if wl.expiration_time >
                  datetime.datetime.now() and wl.valid]
    response = client.get("/whitelist?active_only=true")
    assert response.status_code == 200
    assert len(response.json()) == len(active_wls)

    assert active_wls == [Whitelist.model_validate(
        wl) for wl in response.json()]


def test_get_whitelisted_ckeys(client, whitelist_factory, wl_type):
    assert wl_type != "wrong"  # la stampella - should not happen, but what if
    correct_wls = [whitelist_factory(wl_type=wl_type) for _ in range(5)]
    _ = [whitelist_factory(wl_type="wrong")
         for _ in range(5)]  # Trash wls to test the filter
    response = client.get(f"/whitelist/{wl_type}/ckeys?active_only=false")
    assert response.status_code == 200

    assert len(correct_wls) == len(response.json())
    # TODO: check that the ckeys are the same


def test_post_whitelist_discord(client, player, bearer, wl_type, duration_days):
    new_wl = NewWhitelistDiscord(
        player_discord_id=player.discord_id,
        admin_discord_id=player.discord_id,
        duration_days=duration_days
    )
    response = client.post(
        f"whitelist/{wl_type}/discord",
        json=new_wl.model_dump(),
        headers={"Authorization": f"Bearer {bearer}"}
    )
    assert response.status_code == 201

    wl = Whitelist.model_validate(response.json())

    assert wl.player_id == player.id
    assert wl.admin_id == player.id
    assert wl.wl_type == wl_type
    assert wl.expiration_time > datetime.datetime.now()
    assert wl.valid


def test_post_whitelist_ckey(client, player, bearer, wl_type, duration_days):
    new_wl = NewWhitelistCkey(
        player_ckey=player.ckey,
        admin_ckey=player.ckey,
        duration_days=duration_days
    )
    response = client.post(
        f"whitelist/{wl_type}/ckey",
        json=new_wl.model_dump(),
        headers={"Authorization": f"Bearer {bearer}"}
    )
    assert response.status_code == 201

    wl = Whitelist.model_validate(response.json())

    assert wl.player_id == player.id
    assert wl.admin_id == player.id
    assert wl.wl_type == wl_type
    assert wl.expiration_time > datetime.datetime.now()
    assert wl.valid
