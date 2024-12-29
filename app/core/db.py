from sqlmodel import SQLModel, create_engine

from app.core.config import Config

DBConfig = Config.Database

engine = create_engine(
    f"{DBConfig.ENGINE}://{DBConfig.USER}:{DBConfig.PASSWORD}@{
        DBConfig.HOST}:{DBConfig.PORT}/{DBConfig.NAME}",
    pool_size=DBConfig.POOL_SIZE,
    max_overflow=DBConfig.OVERFLOW,
    pool_recycle=DBConfig.POOL_RECYCLE,
    pool_pre_ping=DBConfig.POOL_PRE_PING,
)


def init_db() -> None:
    if not Config.Database.NEEDS_REBUILD:
        return

    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine, checkfirst=False)
