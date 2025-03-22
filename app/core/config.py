import logging
import os
import tomllib
from collections.abc import Callable
from functools import lru_cache
from typing import Any, BinaryIO, Self, override

from pydantic import BaseModel, Field, ValidationError, field_validator


logger = logging.getLogger(__name__)


class ConfigSection(BaseModel):
    """Base class for all configuration sections."""

    def log_defaults(self) -> None:
        """Log fields that use their default values."""
        for field_name, field_info in self.model_fields.items():
            current_value = getattr(self, field_name)
            default_value = field_info.default

            if current_value == default_value:
                logger.debug("Default used for '%s'", field_name)
            elif isinstance(current_value, ConfigSection):
                logger.debug("Checking nested model: %s", field_name)
                current_value.log_defaults()

    @classmethod
    def env_prefix(cls) -> str:
        return ""

    @classmethod
    def from_env(cls, **kwargs: Any) -> Self:  # noqa: ANN401
        """
        Create an instance with values from environment variables.

        For a field named 'example_field' in a section with _env_prefix = 'APP_',
        it will look for an environment variable APP_EXAMPLE_FIELD.
        """
        data: dict[str, Any] = {}

        for field_name in cls.model_fields:
            env_var_name = f"{cls.env_prefix()}{field_name.upper()}"
            env_value = os.environ.get(env_var_name)

            if env_value is not None:
                data[field_name] = env_value

        # Override with explicit kwargs
        data.update(kwargs)

        return cls.model_validate(data)


class General(ConfigSection):
    """General application configuration."""

    project_name: str = "Space Station Central"
    project_desc: str = (
        "API для объединения множества серверов SS13 и SS14 в одну систему. От него несет вульпой, но он работает."
    )
    project_ver: str = "0.1.0"
    favicon_path: str = "app/assets/favicon.png"
    discord_webhook: str = ""

    @override
    @classmethod
    def env_prefix(cls) -> str:
        return "APP_"

    @field_validator("discord_webhook")
    @classmethod
    def validate_webhook(cls, value: str) -> str:
        if value and not value.startswith(("http://", "https://")):
            logger.warning("Discord webhook URL should start with http:// or https://")
        return value


class Database(ConfigSection):
    """Database connection configuration."""

    engine: str = "postgresql+psycopg2"
    name: str = "central"
    user: str = "root"
    password: str = "root"
    host: str = "127.0.0.1"
    port: int = 5432
    pool_size: int = 10
    overflow: int = 5
    pool_recycle: int = 3600
    pool_pre_ping: bool = True
    echo: bool = False

    @override
    @classmethod
    def env_prefix(cls) -> str:
        return "DB_"

    def get_connection_string(self) -> str:
        """Generate a SQLAlchemy connection string from the config."""
        return f"{self.engine}://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class Redis(ConfigSection):
    """Redis connection configuration."""

    connection_string: str = "redis://127.0.0.1:6379/0"
    channel: str = "central"

    @override
    @classmethod
    def env_prefix(cls) -> str:
        return "REDIS_"


class OAuth(ConfigSection):
    """OAuth configuration for authentication."""

    # From discord app's settings
    client_secret: str = "12345678"
    client_id: int = 12345678
    endpoint_url: str = "http://127.0.0.1:8000/v1"
    discord_server_id: str = "12345678"
    discord_server_invite: str = "https://discord.com/invite/12345678"

    @override
    @classmethod
    def env_prefix(cls) -> str:
        return "OAUTH_"


class AppConfig(ConfigSection):
    """Application configuration root."""

    general: General = Field(default_factory=General)
    database: Database = Field(default_factory=Database)
    redis: Redis = Field(default_factory=Redis)
    oauth: OAuth = Field(default_factory=OAuth)

    @override
    @classmethod
    def env_prefix(cls) -> str:
        return super().env_prefix()


class ConfigLoader:
    """
    Configuration loader that handles different sources with precedence.

    1. Environment variables (highest priority)
    2. Config file (.config.toml)
    3. Project metadata (pyproject.toml)
    4. Default values (lowest priority)
    """

    def __init__(
        self,
        config_stream_provider: Callable[[], BinaryIO] | None = None,
        project_stream_provider: Callable[[], BinaryIO] | None = None,
        env_prefix: str = "",
    ) -> None:
        """
        Initialize the configuration loader.

        Args:
            config_stream_provider : Callable that returns a stream to the config file.
            project_stream_provider : Callable that returns a stream to the project metadata file.
            env_prefix : Prefix for environment variables (default: "")
        """
        self.config_stream_provider = config_stream_provider
        self.project_stream_provider = project_stream_provider
        self.env_prefix = env_prefix

    def _load_toml_file(self, toml_stream: BinaryIO) -> dict[str, Any]:
        """Load and parse a TOML file."""
        try:
            with toml_stream:
                logger.debug("Loading data from a stream...")
                return tomllib.load(toml_stream)
        except tomllib.TOMLDecodeError as e:
            logger.error(f"Error parsing a stream: {e}")
            return {}

    def load(self) -> AppConfig:
        """
        Load configuration from all sources with proper precedence.

        Returns:
            AppConfig
                The validated configuration object

        Raises:
            ValidationError
                If the configuration is invalid

        """
        # Load from streams if available
        config_data: dict[str, Any] = (
            self._load_toml_file(self.config_stream_provider()) if self.config_stream_provider else {}
        )
        project_data: dict[str, Any] = (
            self._load_toml_file(self.project_stream_provider()) if self.project_stream_provider else {}
        )

        # Merge project metadata if available
        if "project" in project_data and "general" in config_data:
            project_meta = project_data["project"]
            if "name" in project_meta and "project_name" not in config_data["general"]:
                config_data["general"]["project_name"] = project_meta["name"]
            if "description" in project_meta and "project_desc" not in config_data["general"]:
                config_data["general"]["project_desc"] = project_meta["description"]
            if "version" in project_meta and "project_ver" not in config_data["general"]:
                config_data["general"]["project_ver"] = project_meta["version"]

        # Create config with data from streams
        try:
            config: AppConfig = AppConfig.model_validate(config_data)

            # Now apply environment variables which take precedence
            if General.env_prefix() in os.environ:
                config.general = General.from_env()
            if Database.env_prefix() in os.environ:
                config.database = Database.from_env()
            if Redis.env_prefix() in os.environ:
                config.redis = Redis.from_env()
            if OAuth.env_prefix() in os.environ:
                config.oauth = OAuth.from_env()

            # Log which values are using defaults
            logger.debug("Checking for default config values...")
            config.log_defaults()

            return config

        except ValidationError as e:
            logger.error(f"Configuration validation error: {e}")
            raise


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """
    Get the application configuration.

    Uses a singleton pattern with lazy loading.

    Returns:
        AppConfig
            The application configuration
    """
    loader = ConfigLoader()
    config = loader.load()
    logger.info("Config loaded.")
    return config
