import logging
import tomllib
from io import BufferedReader
from pathlib import Path

from pydantic import BaseModel, ValidationError


logger = logging.getLogger(__name__)


class CustomBaseModel(BaseModel):
    def log_defaults(self) -> None:
        """Log fields that use their default values."""
        for field_name, field_info in self.model_fields.items():
            current_value = getattr(self, field_name)
            default_value = field_info.default

            if current_value == default_value:
                logger.info("Default used for '%s'", field_name)
            elif isinstance(current_value, CustomBaseModel):
                logger.info("Checking nested model: %s", field_name)
                current_value.log_defaults()


class General(CustomBaseModel):
    project_name: str = "Space Station Central"
    project_desc: str = (
        "API для объеденения множества серверов SS13 и SS14 в одну систему. От него несет вульпой, но он работает."
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


class Config(CustomBaseModel):
    general: General = General()
    database: Database = Database()
    redis: Redis = Redis()
    oauth: OAuth = OAuth()


def parse_config(f: BufferedReader) -> Config:
    logger.info("Using .config.toml")
    data = tomllib.load(f)
    config = Config.model_validate(data)
    logger.info("Checking defaults...")
    config.log_defaults()
    return config


def load_config() -> Config:
    try:
        with Path(".config.toml").open("rb") as f:
            return parse_config(f)
    except FileNotFoundError:
        logger.info("Config file not found, using default.")
        return Config()
    except (tomllib.TOMLDecodeError, ValidationError) as e:
        logger.info("Invalid config file: %s", e)
        raise e


CONFIG = load_config()
logger.info("Config loaded.")
