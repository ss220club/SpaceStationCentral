import io
import tomllib
from collections.abc import Callable
from pathlib import Path
from textwrap import dedent
from typing import BinaryIO

import pytest
from app.core.config import (
    AppConfig,
    DatabaseConfig,
    GeneralConfig,
    SectionedTomlConfigSettingsSource,
    get_config,
)
from pytest_mock import MockerFixture


@pytest.fixture
def mock_config_file() -> Callable[[], BinaryIO]:
    config_content = """
    [general]
    name = "Config Project"
    description = "Config Description"
    version = "1.0.0"
    log_level = "INFO"
    [database]
    name = "config_db"
    user = "config_user"
    password = "config_password"
    [redis]
    connection_string = "redis://localhost:6379/0"
    channel = "config_channel"
    [oauth]
    client_id = 12345678
    redirect_uri = "http://localhost:8000/auth"
    """
    return lambda: io.BytesIO(dedent(config_content).encode())


@pytest.fixture
def mock_project_file() -> Callable[[], BinaryIO]:
    project_content = """
    [project]
    name = "project-name-from-pyproject"
    version = "2.0.0"
    description = "Description from pyproject.toml"
    """
    return lambda: io.BytesIO(dedent(project_content).encode())


@pytest.fixture
def empty_file() -> Callable[[], BinaryIO]:
    return lambda: io.BytesIO(b"")


@pytest.fixture
def mock_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SSC_APP_NAME", "Env Project")
    monkeypatch.setenv("SSC_DB_USER", "env_user")
    monkeypatch.setenv("SSC_OAUTH_CLIENT_ID", "99999999")


class TestSectionedTomlSource:
    def test_extract_section(self, mock_config_file: Callable[[], BinaryIO], tmp_path: Path) -> None:
        config_file = tmp_path / ".config.toml"
        config_file.write_bytes(mock_config_file().read())

        source = SectionedTomlConfigSettingsSource(GeneralConfig, toml_file=str(config_file), section="general")
        config_data = source()

        assert config_data["name"] == "Config Project"
        assert config_data["description"] == "Config Description"
        assert config_data["version"] == "1.0.0"

        assert "database" not in config_data
        assert "user" not in config_data

    def test_missing_section(self, mock_config_file: Callable[[], BinaryIO], tmp_path: Path) -> None:
        config_file = tmp_path / ".config.toml"
        config_file.write_bytes(mock_config_file().read())

        source = SectionedTomlConfigSettingsSource(GeneralConfig, toml_file=str(config_file), section="missing_section")
        config_data = source()

        assert isinstance(config_data, dict)
        assert len(config_data) == 0


class TestGeneralConfig:
    def test_initialization(self) -> None:
        config = GeneralConfig()
        assert config.name == "SpaceStationCentral"
        assert config.description == "SS220 API for game servers and infrastructure"
        assert config.version == "0.1.0"

    def test_validate_webhook_valid(self) -> None:
        config = GeneralConfig(discord_webhook="https://discord.com/api/webhooks/12345/abcdef")
        assert config.discord_webhook == "https://discord.com/api/webhooks/12345/abcdef"

    def test_validate_webhook_invalid(self) -> None:
        with pytest.raises(ValueError):
            GeneralConfig(discord_webhook="invalid-url")


class TestDatabaseConfig:
    def test_connection_string(self) -> None:
        config = DatabaseConfig(
            engine="postgresql+psycopg2",
            name="config_db",
            user="config_user",
            password="config_password",
            host="config.host",
            port=5555,
        )

        assert (
            config.get_connection_string()
            == "postgresql+psycopg2://config_user:config_password@config.host:5555/config_db"
        )


class TestConfigFiles:
    def test_load_from_config_file(self, mocker: MockerFixture, mock_config_file: Callable[[], BinaryIO]) -> None:
        mock_toml_source = mocker.patch("app.core.config.TomlConfigSettingsSource._read_files")
        config_data = tomllib.load(mock_config_file())
        mock_toml_source.return_value = config_data

        config = AppConfig()

        assert config.general.name == "Config Project"
        assert config.general.description == "Config Description"
        assert config.database.name == "config_db"
        assert config.database.user == "config_user"
        assert config.redis.connection_string == "redis://localhost:6379/0"
        assert config.oauth.client_id == 12345678

    def test_load_from_project_file(self, mocker: MockerFixture, mock_project_file: Callable[[], BinaryIO]) -> None:
        mock_pyproject_source = mocker.patch("app.core.config.PyprojectTomlConfigSettingsSource.__call__")
        project_data = tomllib.load(mock_project_file())
        mock_pyproject_source.return_value = project_data["project"]
        config = AppConfig()

        assert config.general.name == "project-name-from-pyproject"
        assert config.general.description == "Description from pyproject.toml"
        assert config.general.version == "2.0.0"

        assert config.database.name == "central"
        assert config.redis.channel == "central"

    def test_load_from_env_vars(self, mock_env_vars: None) -> None:  # noqa: ARG002  # pyright: ignore[reportUnusedParameter]
        config = AppConfig()

        assert config.general.name == "Env Project"
        assert config.database.user == "env_user"
        assert config.oauth.client_id == 99999999

        assert config.general.description == "SS220 API for game servers and infrastructure"
        assert config.database.name == "central"

    def test_option_precedence(
        self,
        mocker: MockerFixture,
        mock_env_vars: None,  # noqa: ARG002  # pyright: ignore[reportUnusedParameter]
    ) -> None:
        mock_toml_source = mocker.patch("app.core.config.TomlConfigSettingsSource._read_files")
        mock_pyproject_source = mocker.patch("app.core.config.PyprojectTomlConfigSettingsSource._read_files")
        mock_toml_source.return_value = {
            "general": {
                "name": "Config Project",
                "description": "Test Description",
                "version": "1.0.0",
            },
            "database": {
                "name": "test_db",
            },
        }

        mock_pyproject_source.return_value = {
            "project": {
                "name": "project-name-from-pyproject",
                "version": "2.0.0",
                "description": "Description from pyproject.toml",
            }
        }

        config = AppConfig()

        # From env vars (highest precedence)
        assert config.general.name == "Env Project"
        assert config.database.user == "env_user"
        assert config.oauth.client_id == 99999999

        # From config file (medium precedence)
        assert config.general.description == "Test Description"  # Not overridden by env
        assert config.database.name == "test_db"  # Not overridden by env

        # Project file values should not be visible where config overrides them
        assert config.general.version == "1.0.0"  # From config, not 2.0.0 from project

    def test_invalid_toml(self, mocker: MockerFixture) -> None:
        mock_toml_source = mocker.patch("app.core.config.TomlConfigSettingsSource.__call__")
        mock_toml_source.side_effect = tomllib.TOMLDecodeError("Invalid TOML", "invalid", 0)

        with pytest.raises(tomllib.TOMLDecodeError):
            AppConfig()


class TestConfigSingleton:
    def test_singleton_pattern(self, monkeypatch: pytest.MonkeyPatch) -> None:
        get_config.cache_clear()

        monkeypatch.setenv("SSC_APP_NAME", "Singleton Test")

        config1 = get_config()
        assert config1.general.name == "Singleton Test"

        # Changing env vars doesn't affect singleton after creation
        monkeypatch.setenv("SSC_APP_NAME", "Changed Name")
        config2 = get_config()

        # Should still have the original env var value
        assert config1 is config2
        assert config2.general.name == "Singleton Test"

        get_config.cache_clear()
        config3 = get_config()

        # Should have the new env var value as singleton is reloaded
        assert config1 is not config3
        assert config3.general.name == "Changed Name"
