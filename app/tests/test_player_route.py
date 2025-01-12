import hashlib
import random

from sqlmodel import select

from app.database.models import Auth, CkeyLinkToken, Player


def test_get_player(client, player):
    response = client.get(f"/player/ckey/{player.ckey}")
    assert response.status_code == 200
    player_result = Player.model_validate(response.json())
    assert player_result == player

    response = client.get(f"/player/discord/{player.discord_id}")
    assert response.status_code == 200
    player_result = Player.model_validate(response.json())
    assert player_result == player


def test_create_token(client, db_session, ckey):
    response = client.post(f"/player/token/{ckey}")
    assert response.status_code == 403
    fake_auth_token = 00000000
    response = client.post(
        f"/player/token/{ckey}", headers={"Authorization": f"Bearer {fake_auth_token}"})
    assert response.status_code == 401

    auth_token = str(random.randint(10000000, 99999999))
    token_hash = hashlib.sha256(auth_token.encode()).hexdigest()

    auth = Auth(token_hash=token_hash)
    db_session.add(auth)
    db_session.commit()

    response = client.post(
        f"/player/token/{ckey}", headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 201

    created_token = db_session.exec(select(CkeyLinkToken).where(
        CkeyLinkToken.token == response.json())).first()
    assert created_token is not None
