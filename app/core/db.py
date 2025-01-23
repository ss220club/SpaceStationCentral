from sqlmodel import SQLModel, create_engine

from app.core.config import CONFIG

DBConfig = CONFIG.database

engine = create_engine(
    f"{DBConfig.engine}://{DBConfig.user}:{DBConfig.password}@{
        DBConfig.host}:{DBConfig.port}/{DBConfig.name}",
    pool_size=DBConfig.pool_size,
    max_overflow=DBConfig.overflow,
    pool_recycle=DBConfig.pool_recycle,
    pool_pre_ping=DBConfig.pool_pre_ping,
)


def init_db() -> None:
    if not CONFIG.database.needs_rebuild:
        return

    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine, checkfirst=False)
