# pylint: disable=redefined-outer-name
from sqlmodel import select
from app.database.models import Player, Whitelist, WhitelistBan
from app.tests.fixtures import (bearer, ckey,  # pylint: disable=unused-import
                                ckey2, client, db_session, discord_id,
                                discord_id2, duration_days)


def test_get_whitelists(client, db_session, discord_id, discord_id2, ckey, ckey2, duration_days):
    player = Player(ckey=ckey, discord_id=discord_id)
    admin = Player(ckey=ckey2, discord_id=discord_id2)
    db_session.add_all([player, admin])
    db_session.commit()

    wl = Whitelist(player_id=discord_id, type="test",
                   admin_id=discord_id2, duration=duration_days)
    db_session.add(wl)
    db_session.commit()
    db_session.refresh(wl)

    response = client.get(f"/whitelist/ckey/{ckey}")
    assert response.status_code == 200
    wl_result = Whitelist.model_validate(response.json()[0])
    assert wl_result == wl

    response = client.get(f"/whitelist/discord/{discord_id}")
    assert response.status_code == 200
    wl_result = Whitelist.model_validate(response.json()[0])
    assert wl_result == wl


def test_post_whitelist(client, db_session, bearer, discord_id, discord_id2, ckey, ckey2, duration_days):
    player = Player(ckey=ckey, discord_id=discord_id)
    admin = Player(ckey=ckey2, discord_id=discord_id2)
    db_session.add_all([player, admin])
    db_session.commit()

    wl = Whitelist(player_id=discord_id, type="test",
                   admin_id=discord_id2, duration=duration_days)

    response = client.post("/whitelist", json=wl.model_dump(mode="json"),
                           headers={"Authorization": f"Bearer {bearer}"})
    assert response.status_code == 201

def test_post_whitelist_ban(client, db_session, bearer, discord_id, discord_id2, ckey, ckey2, duration_days):
    player = Player(ckey=ckey, discord_id=discord_id)
    admin = Player(ckey=ckey2, discord_id=discord_id2)
    db_session.add_all([player, admin])
    db_session.commit()

    wl = Whitelist(player_id=discord_id, type="test",
                   admin_id=discord_id2, duration=duration_days)
    db_session.add(wl)
    db_session.commit()

    wl_ban = WhitelistBan(player_id=discord_id, type="test",
                   admin_id=discord_id2, duration=duration_days)

    response = client.post("/whitelist/ban", json=wl_ban.model_dump(mode="json"),
                           headers={"Authorization": f"Bearer {bearer}"})
    assert response.status_code == 201
    # Make sure old wls detonate
    wl = db_session.exec(select(Whitelist).where(Whitelist.player_id == discord_id)).first()
    assert not wl.valid

def test_pardon_whitelist_ban(client, db_session, bearer, discord_id, discord_id2, ckey, ckey2, duration_days):
    player = Player(ckey=ckey, discord_id=discord_id)
    admin = Player(ckey=ckey2, discord_id=discord_id2)
    db_session.add_all([player, admin])
    db_session.commit()

    wl_ban = WhitelistBan(player_id=discord_id, type="test",
                   admin_id=discord_id2, duration=duration_days)
    db_session.add(wl_ban)
    db_session.commit()
    db_session.refresh(wl_ban)

    response = client.patch(f"/whitelist/ban?ban_id={wl_ban.id}", headers={"Authorization": f"Bearer {bearer}"})
    assert response.status_code == 202

    db_session.refresh(wl_ban)
    assert not wl_ban.valid
