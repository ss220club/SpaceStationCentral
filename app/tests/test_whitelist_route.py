import datetime

from app.database.models import Whitelist


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
