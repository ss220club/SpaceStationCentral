# pylint: disable=redefined-outer-name
import datetime
import hashlib
import random
import string

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.db import engine, init_db
from app.database.models import Auth
from app.main import app


@pytest.fixture(scope="module")
def client():
    yield TestClient(app, base_url="http://127.0.0.1:8000")


@pytest.fixture(scope="module")
def db_session():
    init_db()

    with Session(engine) as session:
        yield session


@pytest.fixture(scope="module")
def bearer(db_session):
    token = str(random.randint(10000000, 99999999))
    hashed_token = hashlib.sha256(token.encode()).hexdigest()

    auth = Auth(token_hash=hashed_token)
    db_session.add(auth)
    db_session.commit()

    yield token


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
    new_ckey = ''.join(random.choices(
        string.ascii_letters + string.digits, k=8))
    yield new_ckey


@pytest.fixture(scope="function")
def ckey2():
    new_ckey = ''.join(random.choices(
        string.ascii_letters + string.digits, k=8))
    yield new_ckey


@pytest.fixture(scope="function")
def duration_days():
    new_duration = datetime.timedelta(days=random.randint(1, 777))
    yield new_duration
