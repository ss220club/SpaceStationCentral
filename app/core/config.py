import logging
from functools import lru_cache
from os import environ
from pathlib import Path
from typing import ClassVar, override

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    PyprojectTomlConfigSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)
from pydantic_settings.sources import PathType


logger = logging.getLogger(__name__)


class ExtendedSettingsConfigDict(SettingsConfigDict, total=False):
    toml_file_section: str | None
    """Section of the TOML file to use when filling variables."""


class ConfigSection(BaseSettings):
    """Base class for all configuration sections."""

    GENERAL_PREFIX: ClassVar[str] = "SSC_"
    CONFIG_FILE_ENV: ClassVar[str] = GENERAL_PREFIX + "CONFIG_FILE"
    CONFIG_FILE_DEFAULT: ClassVar[str] = ".config.toml"

    TEST_ENV: ClassVar[str] = GENERAL_PREFIX + "TEST"

    @override
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            SectionedTomlConfigSettingsSource(cls, toml_file=cls.get_config_file()),
            file_secret_settings,
        )

    @classmethod
    def get_config_file(cls) -> str:
        return environ.get(cls.CONFIG_FILE_ENV) or cls.CONFIG_FILE_DEFAULT

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


class GeneralConfig(ConfigSection):
    """General application configuration."""

    model_config = ExtendedSettingsConfigDict(
        env_prefix=f"{ConfigSection.GENERAL_PREFIX}APP_",
        toml_file_section="general",
        pyproject_toml_table_header=("project",),
        extra="ignore",
    )

    name: str = Field(default="Space Station Central")
    version: str = Field(default="0.1.0")
    description: str = Field(default="API для объединения множества серверов SS13 и SS14 в одну систему.")
    favicon_path: str = Field(default="app/assets/favicon.png")
    discord_webhook: str | None = Field(default=None)

    @override
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            SectionedTomlConfigSettingsSource(cls, toml_file=cls.get_config_file()),
            PyprojectTomlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )

    @field_validator("discord_webhook")
    @classmethod
    def validate_webhook(cls, value: str) -> str:
        if value and not value.startswith(("http://", "https://")):
            raise ValueError("Discord webhook URL should start with http:// or https://")
        return value


class DatabaseConfig(ConfigSection):
    """Database connection configuration."""

    model_config = ExtendedSettingsConfigDict(
        env_prefix=f"{ConfigSection.GENERAL_PREFIX}DB_", toml_file_section="database", extra="ignore"
    )

    engine: str = Field(default="postgresql+psycopg2")
    name: str = Field(default="central")
    user: str = Field(default="root")
    password: str = Field(default="root")
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=5432)
    pool_size: int = Field(default=10)
    overflow: int = Field(default=5)
    pool_recycle: int = Field(default=3600)
    pool_pre_ping: bool = Field(default=True)
    echo: bool = Field(default=False)

    def get_connection_string(self) -> str:
        """Generate a SQLAlchemy connection string from the config."""
        return f"{self.engine}://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class RedisConfig(ConfigSection):
    """Redis connection configuration."""

    model_config = ExtendedSettingsConfigDict(
        env_prefix=f"{ConfigSection.GENERAL_PREFIX}REDIS_", toml_file_section="redis", extra="ignore"
    )

    connection_string: str = Field(default="redis://127.0.0.1:6379/0")
    channel: str = Field(default="central")


class OAuthConfig(ConfigSection):
    """OAuth configuration for authentication."""

    model_config = ExtendedSettingsConfigDict(
        env_prefix=f"{ConfigSection.GENERAL_PREFIX}OAUTH_", toml_file_section="oauth", extra="ignore"
    )

    # From discord app's settings
    client_secret: str = Field(default="12345678")
    client_id: int = Field(default=12345678)
    endpoint_url: str = Field(default="http://127.0.0.1:8000/v1")
    discord_server_id: str = Field(default="12345678")
    discord_server_invite: str = Field(default="https://discord.com/invite/12345678")


class AppConfig(BaseModel):
    """Application configuration root."""

    general: GeneralConfig = Field(default_factory=GeneralConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    oauth: OAuthConfig = Field(default_factory=OAuthConfig)


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """
    Get the application configuration.

    Uses a singleton pattern with lazy loading.

    Returns:
        The application configuration
    """
    config = AppConfig()
    logger.info("Config loaded.")
    return config


class SectionedTomlConfigSettingsSource(TomlConfigSettingsSource):
    """Source of configuration from TOML with section support."""

    DEFAULT_PATH: ClassVar[Path] = Path()

    def __init__(
        self,
        settings_cls: type[BaseSettings],
        toml_file: PathType | None = DEFAULT_PATH,
        section: str | None = None,
    ) -> None:
        self.toml_file_path = (
            toml_file if toml_file != self.DEFAULT_PATH else settings_cls.model_config.get("toml_file")
        )
        self.section = section or settings_cls.model_config.get("toml_file_section")
        self.toml_data = self._read_files(self.toml_file_path)
        if self.section:
            self.toml_data = self.toml_data.get(self.section, {})
        super(TomlConfigSettingsSource, self).__init__(settings_cls, self.toml_data)
