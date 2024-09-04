from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import Session

from config import Config

db_config = Config.Database

engine = create_async_engine(
    f"{db_config.ENGINE}://{db_config.USER}:{db_config.PASSWORD}@{db_config.HOST}:{db_config.PORT}/{db_config.NAME}",
    pool_size=db_config.POOL_SIZE,
    max_overflow=db_config.OVERFLOW,
    pool_recycle=db_config.POOL_RECYCLE,
    pool_pre_ping=db_config.POOl_PRE_PING,
    )

def init_db(session: Session) -> None:
    pass