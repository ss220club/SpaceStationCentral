import random
import string
from collections.abc import Callable, Generator
from datetime import datetime, timedelta

import pytest
from app.core.utils import utcnow2
from app.database.crud.player import create_player
from app.database.models import ApiAuth, Player, Whitelist
from app.deps import get_session, hash_bearer_token
from app.main import app as main_app
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine


# The sqlalchemy fireaxe. Open in case of emergemncy
# import logging
# logging.getLogger("sqlalchemy.engine").setLevel(logging.DEBUG)


@pytest.fixture(scope="session")
def app() -> Generator[FastAPI]:
    yield main_app


@pytest.fixture(scope="session")
def client(app: FastAPI) -> Generator[TestClient]:
    yield TestClient(app, base_url="http://127.0.0.1:8000/")


@pytest.fixture(scope="function")
def db_session() -> Generator[Session]:
    # Create an in-memory SQLite database engine
    # sqlite_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    sqlite_engine = create_engine("sqlite:///ci.db", connect_args={"check_same_thread": False})

    # Create all tables in the in-memory SQLite database
    SQLModel.metadata.drop_all(sqlite_engine)
    SQLModel.metadata.create_all(sqlite_engine)

    # Return a session to the in-memory SQLite database
    with Session(sqlite_engine) as session:
        yield session

    # Drop all tables in the in-memory SQLite database
    SQLModel.metadata.drop_all(sqlite_engine)
    # Close the in-memory SQLite database engine
    sqlite_engine.dispose()


@pytest.fixture(scope="function", autouse=True)
def override_session(app: FastAPI, db_session: Session) -> Generator[None]:
    app.dependency_overrides[get_session] = lambda: db_session
    yield
    app.dependency_overrides = {}


@pytest.fixture(scope="function")
def bearer(db_session: Session) -> Generator[str]:
    token = str(random.randint(10000000, 99999999))
    hashed_token = hash_bearer_token(token)

    auth = ApiAuth(token_hash=hashed_token)
    db_session.add(auth)
    db_session.commit()

    yield token


def generate_discord_id() -> str:
    return str(random.randint(100000000000000000, 999999999999999999))


@pytest.fixture(scope="function")
def discord_id() -> Generator[str]:
    yield generate_discord_id()


def generate_ckey() -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=8))


@pytest.fixture(scope="function")
def ckey() -> Generator[str]:
    yield generate_ckey()


@pytest.fixture(scope="function")
def player(db_session: Session, ckey: str, discord_id: str) -> Generator[Player]:
    yield create_player(db_session, ckey, discord_id)


@pytest.fixture(scope="function")
def player_factory(db_session: Session) -> Generator[Callable[[str | None, str | None], Player]]:
    def factory(ckey: str | None = None, discord_id: str | None = None) -> Player:
        ckey = ckey if ckey is not None else generate_ckey()
        discord_id = discord_id if discord_id is not None else generate_discord_id()
        return create_player(db_session, ckey, discord_id)

    yield factory  # type: ignore


@pytest.fixture(scope="function")
def duration_days() -> Generator[int]:
    yield random.randint(1, 777)


def generate_server_type() -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=8))


@pytest.fixture(scope="function")
def server_type() -> Generator[str]:
    yield generate_server_type()


def create_whitelist(
    db_session: Session,
    player: Player,
    admin: Player,
    server_type: str,
    expiration_time: datetime,
    valid: bool,
) -> Whitelist:
    wl = Whitelist(
        player_id=player.id,  # pyright: ignore[reportArgumentType]
        admin_id=admin.id,  # pyright: ignore[reportArgumentType]
        server_type=server_type,
        expiration_time=expiration_time,
        valid=valid,
    )
    db_session.add(wl)
    db_session.commit()
    db_session.refresh(wl)
    return wl


@pytest.fixture(scope="function")
def whitelist(
    db_session: Session,
    player: Player,
    admin: Player,
    server_type: str,
    expiration_time: datetime,
    valid: bool,
) -> Generator[Whitelist]:
    yield create_whitelist(db_session, player, admin, server_type, expiration_time, valid)


@pytest.fixture(scope="function")
def whitelist_factory(db_session: Session) -> Generator[Callable[..., Whitelist]]:
    def factory(
        player: Player | None = None,
        admin: Player | None = None,
        server_type: str | None = None,
        expiration_time: datetime | None = None,
        valid: bool = True,
    ) -> Whitelist:
        player = player if player is not None else create_player(db_session, generate_ckey(), generate_discord_id())
        admin = admin if admin is not None else create_player(db_session, generate_ckey(), generate_discord_id())
        server_type = server_type if server_type is not None else generate_server_type()
        expiration_time = (
            expiration_time if expiration_time is not None else utcnow2() + timedelta(days=random.randint(-777, 777))
        )
        valid = valid or random.choice([True, False])
        return create_whitelist(db_session, player, admin, server_type, expiration_time, valid)

    yield factory
