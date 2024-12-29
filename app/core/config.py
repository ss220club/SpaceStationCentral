import logging
logger = logging.getLogger("main-logger")

# pylint: disable=R0903
class Config:
    class Database:
        ENGINE: str = "postgresql+psycopg2"
        NAME: str = "central"
        USER: str = "root"
        PASSWORD: str = "root"
        HOST: str = "127.0.0.1"
        PORT: int = 5432

        POOL_SIZE: int = 10
        OVERFLOW: int = 5
        POOL_RECYCLE: int = 3600
        POOL_PRE_PING: bool = True

        NEEDS_REBUILD: bool = True

    class Oauth:
        # From discord app's settings
        CLEINT_SECRET: str = "12345678"
        CLIENT_ID: int = 12345678

    class General:
        PROJECT_NAME: str = "FurFur Central"
        PROJECT_DESC: str = "API для объеденения множества серверов SS13 и SS14 в одну систему."
        PROJECT_VER: str = "0.0.1"
        ENDPOINT_URL: str = "http://127.0.0.1:8000"
        FAVICON_PATH: str = "app/assets/favicon.png"


try:
    with open(".prod_config.py", "r", encoding="utf-8") as f:
        logger.info("Using .prod_config.py")
        exec(f.read()) # pylint: disable=exec-used

except FileNotFoundError:
    logger.info("Using default config")
