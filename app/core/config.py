class Config:
    class Database:
        ENGINE = "postgresql+psycopg2"
        NAME: str = "central"
        USER: str = "furior"
        PASSWORD: str = "12345678"
        HOST: str = "127.0.0.1"
        PORT: int = 5432

        POOL_SIZE: int = 10
        OVERFLOW: int = 5
        POOL_RECYCLE: int = 3600
        POOL_PRE_PING: bool = True

        NEEDS_REBUILD: bool = True

    class General:
        PROJECT_NAME: str = "FurFur Central"
        PROJECT_DESC: str = "API для объеденения множества серверов SS13 и SS14 в одну систему."
        PROJECT_VER: str = "0.0.1"