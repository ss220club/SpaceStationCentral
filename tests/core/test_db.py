# pyright: reportPrivateUsage=false
import contextlib
from collections.abc import Generator

import pytest
from app.core.config import DatabaseConfig
from app.core.db import DatabaseClient, get_db_client
from pytest_mock import MockerFixture
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session


@pytest.fixture
def mock_db_config(mocker: MockerFixture) -> DatabaseConfig:
    mock_config = mocker.MagicMock(spec=DatabaseConfig)
    mock_config.get_connection_string.return_value = "postgresql://user:pass@localhost/db"
    mock_config.pool_size = 10
    mock_config.overflow = 20
    mock_config.pool_recycle = 300
    mock_config.pool_pre_ping = True
    mock_config.echo = True
    return mock_config


class TestDatabaseClient:
    def test_init_no_values(self) -> None:
        with pytest.raises(ValueError, match="Either connection_string or config must be provided"):
            DatabaseClient()

    def test_init_with_args(self) -> None:
        connection_string = "sqlite:///test.db"
        client = DatabaseClient(connection_string=connection_string, echo=True)

        assert client._connection_string == connection_string
        assert client._echo is True

    def test_init_with_config(self, mock_db_config: DatabaseConfig) -> None:
        client = DatabaseClient(config=mock_db_config)

        assert client._connection_string == "postgresql://user:pass@localhost/db"
        assert client._pool_size == 10
        assert client._max_overflow == 20
        assert client._pool_recycle == 300
        assert client._pool_pre_ping is True
        assert client._echo is True

    def test_from_config(self, mocker: MockerFixture, mock_db_config: DatabaseConfig) -> None:
        mock_app_config = mocker.MagicMock()
        mock_app_config.database = mock_db_config
        mocker.patch("app.core.db.get_config", return_value=mock_app_config)

        client = DatabaseClient.from_config()

        assert client._connection_string == "postgresql://user:pass@localhost/db"
        assert client._pool_size == 10
        assert client._max_overflow == 20
        assert client._pool_recycle == 300
        assert client._pool_pre_ping is True
        assert client._echo is True

    def test_engine_lazy_creation(self, mocker: MockerFixture, mock_db_config: DatabaseConfig) -> None:
        mock_engine = mocker.MagicMock(spec=Engine)
        mock_create_engine = mocker.patch("app.core.db.create_engine", return_value=mock_engine)

        client = DatabaseClient(config=mock_db_config)

        assert client._engine is None

        mock_create_engine.assert_not_called()
        engine = client.engine

        assert engine is mock_engine
        mock_create_engine.assert_called_once_with(
            "postgresql://user:pass@localhost/db",
            pool_size=10,
            max_overflow=20,
            pool_recycle=300,
            pool_pre_ping=True,
            echo=True,
        )

        # Second access should reuse the same engine
        engine2 = client.engine
        assert engine2 is engine
        assert mock_create_engine.call_count == 1

    def test_session_factory_lazy_creation(self, mocker: MockerFixture, mock_db_config: DatabaseConfig) -> None:
        mock_session_maker = mocker.patch("app.core.db.sessionmaker")
        mock_engine = mocker.MagicMock(spec=Engine)

        client = DatabaseClient(config=mock_db_config)
        client._engine = mock_engine

        assert client._session_factory is None
        mock_session_maker.assert_not_called()

        _ = client.session_factory

        mock_session_maker.assert_called_once_with(autocommit=False, autoflush=False, bind=mock_engine, class_=Session)

    def test_session_context_manager(self, mocker: MockerFixture, mock_db_config: DatabaseConfig) -> None:
        mock_session = mocker.MagicMock(spec=Session)
        mock_factory = mocker.MagicMock(return_value=mock_session)
        mocker.patch.object(DatabaseClient, "session_factory", mock_factory)

        client = DatabaseClient(config=mock_db_config)

        with client.session() as session:
            assert session is mock_session
            session.execute(text("SELECT 1"))  # pyright: ignore[reportDeprecated]

        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

        # Test error handling and rollback
        mock_session.reset_mock()
        mock_session.execute.side_effect = SQLAlchemyError("Test error")

        with pytest.raises(SQLAlchemyError), client.session() as session:
            session.execute(text("SELECT 1"))  # pyright: ignore[reportDeprecated]

        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

    def test_execute(self, mocker: MockerFixture, mock_db_config: DatabaseConfig) -> None:
        mock_result = mocker.MagicMock()
        mock_session = mocker.MagicMock(spec=Session)
        mock_session.execute.return_value = mock_result

        @contextlib.contextmanager
        def mock_session_ctx() -> Generator[Session]:
            yield mock_session

        client = DatabaseClient(config=mock_db_config)
        mocker.patch.object(client, "session", mock_session_ctx)

        result = client.execute(text("SELECT 1"))

        assert result is mock_result
        mock_session.execute.assert_called_once()

    def test_check_connection_success(self, mocker: MockerFixture, mock_db_config: DatabaseConfig) -> None:
        mock_connection = mocker.MagicMock()
        mock_engine = mocker.MagicMock(spec=Engine)
        mock_engine.connect.return_value.__enter__.return_value = mock_connection

        client = DatabaseClient(config=mock_db_config)
        client._engine = mock_engine

        result = client.check_connection()

        assert result is True
        assert mock_connection.execute.call_count == 1

        call_arg = mock_connection.execute.call_args.args
        text_arg = call_arg[0]
        assert str(text_arg) == "SELECT 1"

    def test_check_connection_failure(self, mocker: MockerFixture, mock_db_config: DatabaseConfig) -> None:
        mock_engine = mocker.MagicMock(spec=Engine)
        mock_engine.connect.side_effect = SQLAlchemyError("Connection error")

        mocker.patch.object(DatabaseClient, "engine", mock_engine)

        client = DatabaseClient(config=mock_db_config)
        result = client.check_connection()

        assert result is False

    def test_close(self, mocker: MockerFixture, mock_db_config: DatabaseConfig) -> None:
        mock_engine = mocker.MagicMock(spec=Engine)

        client = DatabaseClient(config=mock_db_config)
        client._engine = mock_engine

        client.close()

        mock_engine.dispose.assert_called_once()
        assert client._engine is None


class TestGetDbClient:
    def test_get_db_client_singleton(self, mocker: MockerFixture) -> None:
        get_db_client.cache_clear()

        mock_client = mocker.MagicMock(spec=DatabaseClient)
        from_config_mock = mocker.patch("app.core.db.DatabaseClient.from_config", return_value=mock_client)

        client1 = get_db_client()
        assert client1 is mock_client

        client2 = get_db_client()
        assert client2 is client1

        from_config_mock.assert_called_once()
