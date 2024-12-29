# pylint: disable=redefined-outer-name
from app.database.models import Player, Whitelist

from app.tests.fixtures import client, db_session, bearer, discord_id, discord_id2, ckey, ckey2, duration_days # pylint: disable=unused-import

def test_get_whitelists(client, db_session, discord_id, discord_id2, ckey, ckey2, duration_days):
    player = Player(ckey=ckey, discord_id=discord_id)
    admin = Player(ckey=ckey2, discord_id=discord_id2)
    db_session.add_all([player, admin])
    db_session.commit()

    wl = Whitelist(player_id=discord_id, type="test", admin_id=discord_id2, duration=duration_days)
    db_session.add(wl)
    db_session.commit()
    db_session.refresh(wl)

    response = client.get(f"/whitelist/ckey/{ckey}")
    assert response.status_code == 200
    wl_result = Whitelist.model_validate(response.json()[0])
    assert wl_result == wl
    

def test_post_whitelist(client, db_session, bearer, discord_id, discord_id2, ckey, ckey2, duration_days):
    player = Player(ckey=ckey, discord_id=discord_id)
    admin = Player(ckey=ckey2, discord_id=discord_id2)
    db_session.add_all([player, admin])
    db_session.commit()

    wl = Whitelist(player_id=discord_id, type="test", admin_id=discord_id2, duration=duration_days)

    response = client.post("/whitelist", json=wl.model_dump(mode="json"), headers={"Authorization": f"Bearer {bearer}"})
    assert response.status_code == 201