import random
import string
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import app
from app.core.db import engine

@pytest.fixture(scope="module")
def client():
    test_client = TestClient(app, base_url="http://127.0.0.1:8000")
    yield test_client


@pytest.fixture(scope="module")
def db_session():
    with Session(engine) as session:
        yield session


@pytest.fixture(scope="function")
def discord_id():
    discord_id = random.randint(100000000000000000, 999999999999999999)
    yield discord_id

@pytest.fixture(scope="function")
def discord_id2():
    discord_id = random.randint(100000000000000000, 999999999999999999)
    yield discord_id

@pytest.fixture(scope="function")
def ckey():
    ckey = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    yield ckey
