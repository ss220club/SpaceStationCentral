import logging
from collections.abc import Generator
from contextlib import contextmanager
from functools import lru_cache
from logging import Logger
from typing import Any

from sqlalchemy import Engine, Executable, Result, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session

from app.core.config import DatabaseConfig, get_config


class DatabaseClient:
    """
    Database client manager for SQLAlchemy operations.

    This class handles database connection management, session creation,
    and provides utility methods for both synchronous and asynchronous operations.
    """

    logger: Logger = logging.getLogger(__name__)

    def __init__(
        self,
        connection_string: str | None = None,
        config: DatabaseConfig | None = None,
        echo: bool | None = None,
        pool_size: int | None = None,
        max_overflow: int | None = None,
        pool_recycle: int | None = None,
        pool_pre_ping: bool | None = None,
    ) -> None:
        """
        Initialize the database client.

        Args:
            connection_string: SQLAlchemy connection string, if None will use the connection string from config
            config: Database configuration, if None will use the default config
            echo: Whether to echo SQL statements for debugging
            pool_size: Connection pool size, if None will use value from config
            max_overflow: Maximum overflow connections, if None will use value from config
            pool_recycle: Time (in seconds) before connections are recycled, if None will use value from config
            pool_pre_ping: Whether to enable connection pool pre-ping, if None will use value from config
        """
        # Build connection string if not provided
        if connection_string is None and config is not None:
            connection_string = config.get_connection_string()

        if connection_string is None:
            raise ValueError("Either connection_string or config must be provided")

        self._connection_string = connection_string

        # Set parameters with priority: explicit params > config > defaults
        self._pool_size = pool_size if pool_size is not None else (config.pool_size if config else 10)
        self._max_overflow = max_overflow if max_overflow is not None else (config.overflow if config else 5)
        self._pool_recycle = pool_recycle if pool_recycle is not None else (config.pool_recycle if config else 3600)
        self._pool_pre_ping = pool_pre_ping if pool_pre_ping is not None else (config.pool_pre_ping if config else True)
        self._echo = echo if echo is not None else (config.echo if config else False)

        # Initialize engine as None, will be created on demand
        self._engine: Engine | None = None

        # Initialize session factory as None, will be created on demand
        self._session_factory: sessionmaker[Session] | None = None

        self.logger.debug("DatabaseClient initialized with connection string: %s", connection_string)

    @classmethod
    def from_config(cls) -> "DatabaseClient":
        """
        Create a database client from app configuration.

        Returns:
            Configured database client
        """
        config = get_config()
        return cls(config=config.database)

    @property
    def engine(self) -> Engine:
        """
        Get the synchronous SQLAlchemy engine, creating it if necessary.

        Returns:
            SQLAlchemy engine
        """
        if self._engine is None:
            self._engine = create_engine(
                self._connection_string,
                echo=self._echo,
                pool_size=self._pool_size,
                max_overflow=self._max_overflow,
                pool_recycle=self._pool_recycle,
                pool_pre_ping=self._pool_pre_ping,
            )
            self.logger.debug("Created synchronous SQLAlchemy engine")
        return self._engine

    @property
    def session_factory(self) -> sessionmaker[Session]:
        """
        Get the synchronous session factory, creating it if necessary.

        Returns:
            SQLAlchemy session factory
        """
        if self._session_factory is None:
            self._session_factory = sessionmaker(autocommit=False, autoflush=False, bind=self.engine, class_=Session)
            self.logger.debug("Created synchronous session factory")
        return self._session_factory

    @contextmanager
    def session(self) -> Generator[Session]:
        """
        Get a synchronous database session.

        Usage:
        ```python
        with db_client.session() as session:
            result = session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
        ```

        Yields:
            SQLAlchemy session
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error("Database error: %s", str(e))
            raise
        finally:
            session.close()

    def execute(self, statement: Executable) -> Result[Any]:
        """
        Execute a SQL statement and return the result.

        Args:
            statement: SQLAlchemy statement to execute

        Returns:
            Result of the statement execution
        """
        with self.session() as session:
            return session.execute(statement)  # pyright: ignore[reportDeprecated]

    def check_connection(self) -> bool:
        """
        Check if the database connection is working.

        Returns:
            True if connection is working, False otherwise
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            self.logger.debug("Database connection check passed")
            return True
        except SQLAlchemyError as e:
            self.logger.error("Database connection check failed: %s", str(e))
            return False

    def close(self) -> None:
        """Close all database connections."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
            self.logger.debug("Closed sync engine")


@lru_cache(maxsize=1)
def get_db_client() -> DatabaseClient:
    """
    Get or create the default database client.

    Returns:
    The default database client
    """
    return DatabaseClient.from_config()
