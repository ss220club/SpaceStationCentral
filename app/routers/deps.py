from collections.abc import AsyncGenerator
from typing import Annotated
from fastapi import Depends
from sqlmodel import Session

from app.core.db import engine

async def get_db() -> AsyncGenerator[Session, None, None]:
    async with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_db)]