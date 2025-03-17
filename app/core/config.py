import logging
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError


logger = logging.getLogger(__name__)


class CustomBaseModel(BaseModel):
    def log_defaults(self) -> None:
        """Log fields that use their default values."""
        for field_name, field_info in self.model_fields.items():
            current_value = getattr(self, field_name)
            default_value = field_info.default

            if current_value == default_value:
                logger.debug("Default used for '%s'", field_name)
            elif isinstance(current_value, CustomBaseModel):
                logger.debug("Checking nested model: %s", field_name)
                current_value.log_defaults()


class General(CustomBaseModel):
    project_name: str = "Space Station Central"
    project_desc: str = (
        "API для объединения множества серверов SS13 и SS14 в одну систему. От него несет вульпой, но он работает."
    )
    project_ver: str = "0.1.0"
    favicon_path: str = "app/assets/favicon.png"


class Database(CustomBaseModel):
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


class Redis(CustomBaseModel):
    connection_string: str = "redis://127.0.0.1:6379/0"
    channel: str = "central"


class OAuth(CustomBaseModel):
    # From discord app's settings
    client_secret: str = "12345678"
    client_id: int = 12345678
    endpoint_url: str = "http://127.0.0.1:8000/v1"

    discord_server_id: str = "12345678"
    discord_server_invite: str = "https://discord.com/invite/12345678"


class Config(CustomBaseModel):
    general: General = General()
    database: Database = Database()
    redis: Redis = Redis()
    oauth: OAuth = OAuth()


def validate_config(data: dict[str, Any]) -> Config:
    config = Config.model_validate(data)
    logger.debug("Checking defaults...")
    config.log_defaults()
    return config


def load_config() -> Config:
    try:
        with Path(".config.toml").open("rb") as f:
            logger.info("Loading config data...")
            config_data = tomllib.load(f)
        with Path("pyproject.toml").open("rb") as f:
            logger.info("Loading project metadata...")
            project_metadata = tomllib.load(f)

        composite_data = config_data.copy()

        if "project_name" not in composite_data["general"]:
            composite_data["general"]["project_name"] = project_metadata["project"]["name"]
        if "project_desc" not in composite_data["general"]:
            composite_data["general"]["project_desc"] = project_metadata["project"]["description"]
        if "project_ver" not in composite_data["general"]:
            composite_data["general"]["project_ver"] = project_metadata["project"]["version"]

        return validate_config(composite_data)
    except FileNotFoundError as e:
        logger.warning("File %s was not found, using default config.", e.filename)
        return Config()
    except (tomllib.TOMLDecodeError, ValidationError) as e:
        logger.info("Invalid config file: %s", e)
        raise e


CONFIG = load_config()
logger.info("Config loaded.")
