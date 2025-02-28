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
"""
SQLModel doesnt natively support async engines
TODO: Use SQLAlchemy's async engine
"""

def init_db() -> None:
    return
