from io import BufferedReader
from pydantic import BaseModel, ValidationError
import tomllib

# Logging isnt initialized yet at this point, so uses prints

# pylint: disable=R0903


class CustomBaseModel(BaseModel):
    def log_defaults(self) -> None:
        """Log fields that use their default values."""
        for field_name in self.model_fields:
            current_value = getattr(self, field_name)
            default_value = self.model_fields[field_name].default

            if current_value == default_value:
                print(f"Default used for '{field_name}'")
            elif isinstance(current_value, CustomBaseModel):
                # Recursively check nested Pydantic models
                print(f"Checking nested model: {field_name}")
                current_value.log_defaults()


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

    needs_rebuild: bool = True


class OAuth(CustomBaseModel):
    # From discord app's settings
    client_secret: str = "12345678"
    client_id: int = 12345678


class General(CustomBaseModel):
    project_name: str = "FurFur Central"
    project_desc: str = "API для объеденения множества серверов SS13 и SS14 в одну систему."
    project_ver: str = "0.0.1"
    endpoint_url: str = "http://127.0.0.1:8000"
    favicon_path: str = "app/assets/favicon.png"


class Config(CustomBaseModel):
    database: Database = Database()
    oauth: OAuth = OAuth()
    general: General = General()


def parse_config(f: BufferedReader) -> Config:
    print("Using .config.toml")
    data = tomllib.load(f)
    config = Config.model_validate(data)
    print("Checking defaults...")
    config.log_defaults()
    return config


def load_config() -> Config:
    try:
        with open(".config.toml", "rb") as f:
            return parse_config(f)
    except FileNotFoundError:
        print("Config file not found, using default.")
        return Config()
    except (tomllib.TOMLDecodeError, ValidationError) as e:
        print(f"Invalid config file: {e}")
        raise e


CONFIG = load_config()
print("Config loaded.")
