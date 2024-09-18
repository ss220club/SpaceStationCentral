from sqlmodel import SQLModel, Session, create_engine
import app.database.models
from app.core.config import Config

db_config = Config.Database

engine = create_engine(
    f"{db_config.ENGINE}://{db_config.USER}:{db_config.PASSWORD}@{db_config.HOST}:{db_config.PORT}/{db_config.NAME}",
    pool_size=db_config.POOL_SIZE,
    max_overflow=db_config.OVERFLOW,
    pool_recycle=db_config.POOL_RECYCLE,
    pool_pre_ping=db_config.POOL_PRE_PING,  
    )

def init_db() -> None:
    if not Config.Database.NEEDS_REBUILD:
        return

    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine, checkfirst=False)
