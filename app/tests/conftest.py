# pylint: disable=redefined-outer-name
import datetime
import random
import string

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from app.database.models import Auth, Player, Whitelist
from app.deps import get_session, hash_bearer_token
from app.main import app as main_app


@pytest.fixture(scope="session")
def app():
    yield main_app


@pytest.fixture(scope="session")
def client(app: FastAPI):
    yield TestClient(app, base_url="http://127.0.0.1:8000")


@pytest.fixture(scope="function")
def db_session():
    

    # Create an in-memory SQLite database engine
    # sqlite_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    sqlite_engine = create_engine(
        "sqlite:///ci.db", connect_args={"check_same_thread": False})

    # Create all tables in the in-memory SQLite database
    SQLModel.metadata.drop_all(sqlite_engine)
    SQLModel.metadata.create_all(sqlite_engine)

    # Return a session to the in-memory SQLite database
    with Session(sqlite_engine) as session:
        yield session


@pytest.fixture(scope="function", autouse=True)
def override_session(app, db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    yield
    app.dependency_overrides = {}


@pytest.fixture(scope="function")
def bearer(db_session: Session):
    token = str(random.randint(10000000, 99999999))
    hashed_token = hash_bearer_token(token)

    auth = Auth(token_hash=hashed_token)
    db_session.add(auth)
    db_session.commit()

    yield token


def generate_discord_id():
    return str(random.randint(100000000000000000, 999999999999999999))


@pytest.fixture(scope="function")
def discord_id():
    yield generate_discord_id()


def generate_ckey():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))


@pytest.fixture(scope="function")
def ckey():
    yield generate_ckey()


def create_player(db_session: Session, ckey: str, discord_id: str):
    player = Player(ckey=ckey, discord_id=discord_id)
    db_session.add(player)
    db_session.commit()
    db_session.refresh(player)
    return player


@pytest.fixture(scope="function")
def player(db_session: Session, ckey: str, discord_id: str):
    yield create_player(db_session, ckey, discord_id)


@pytest.fixture(scope="function")
def player_factory(db_session: Session):
    def factory(ckey: str | None = None, discord_id: str | None = None):
        ckey = ckey if ckey is not None else generate_ckey()
        discord_id = discord_id if discord_id is not None else generate_discord_id()
        return create_player(db_session, ckey, discord_id)
    yield factory


@pytest.fixture(scope="function")
def duration_days():
    yield datetime.timedelta(days=random.randint(1, 777))


def generate_wl_type():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))


@pytest.fixture(scope="function")
def wl_type():
    yield generate_wl_type()


def create_whitelist(db_session: Session, player: Player, admin: Player, wl_type: str, expiration_time: datetime.datetime, valid: bool):
    wl = Whitelist(
        player_id=player.id,
        admin_id=admin.id,
        wl_type=wl_type,
        expiration_time=expiration_time,
        valid=valid
    )
    db_session.add(wl)
    db_session.commit()
    db_session.refresh(wl)
    return wl


@pytest.fixture(scope="function")
def whitelist(db_session: Session, player: Player, admin: Player, wl_type: str, expiration_time: datetime.datetime, valid: bool):
    yield create_whitelist(db_session, player, admin, wl_type, expiration_time, valid)


@pytest.fixture(scope="function")
def whitelist_factory(db_session: Session):
    def factory(player: Player | None = None,
                admin: Player | None = None,
                wl_type: str | None = None,
                expiration_time: datetime.datetime | None = None,
                valid: bool = None) -> Whitelist:
        player = player if player is not None else create_player(
            db_session, generate_ckey(), generate_discord_id())
        admin = admin if admin is not None else create_player(
            db_session, generate_ckey(), generate_discord_id())
        wl_type = wl_type if wl_type is not None else generate_wl_type()
        expiration_time = expiration_time if expiration_time is not None else datetime.datetime.now(
        ) + datetime.timedelta(days=random.randint(-777, 777))
        valid = valid if valid is not None else random.choice([True, False])
        return create_whitelist(db_session, player, admin, wl_type, expiration_time, valid)
    yield factory
