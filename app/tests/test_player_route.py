# pylint: disable=redefined-outer-name
import hashlib
import random
import string
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.database.models import Auth, Player
from app.main import app
from app.core.db import engine, init_db

@pytest.fixture(scope="module")
def client():
    test_client = TestClient(app, base_url="http://127.0.0.1:8000")
    yield test_client


@pytest.fixture(scope="module")
def db_session():
    init_db()

    with Session(engine) as session:
        yield session


@pytest.fixture(scope="function")
def discord_id():
    d_id = random.randint(100000000000000000, 999999999999999999)
    yield str(d_id)

@pytest.fixture(scope="function")
def discord_id2():
    d_id = random.randint(100000000000000000, 999999999999999999)
    yield str(d_id)

@pytest.fixture(scope="function")
def ckey():
    new_ckey = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    yield new_ckey

def test_get_player(client, db_session, discord_id, ckey):
    player = Player(ckey=ckey, discord_id=discord_id)
    db_session.add(player)
    db_session.commit()

    response = client.get(f"/player/ckey/{ckey}")
    assert response.status_code == 200
    player_json = response.json()
    assert player_json["discord_id"] == discord_id
    assert player_json["ckey"] == ckey

    response = client.get(f"/player/discord/{discord_id}")
    assert response.status_code == 200
    player_json = response.json()
    assert player_json["discord_id"] == discord_id
    assert player_json["ckey"] == ckey

def test_create_token(client, db_session, ckey):
    response = client.get(f"/player/token/{ckey}")
    assert response.status_code == 403
    fake_token = 00000000
    response = client.get(f"/player/token/{ckey}", headers={"Authorization": f"Bearer {fake_token}"})
    assert response.status_code == 401

    token = str(random.randint(10000000, 99999999))
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    auth = Auth(token_hash=token_hash)
    db_session.add(auth)
    db_session.commit()

    response = client.get(f"/player/token/{ckey}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
