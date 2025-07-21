import hashlib
from collections.abc import Generator
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from app.core.db import get_db_client
from app.database.models import ApiAuth


def get_session() -> Generator[Session, Any, Any]:
    with get_db_client().session_factory() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def hash_bearer_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


AUTH_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_401_UNAUTHORIZED: {
        "description": "Invalid or missing bearer token",
    }
}


BEARER_SCHEME = HTTPBearer()
HTTPAuthCredDep = Depends(BEARER_SCHEME)


def verify_bearer(session: SessionDep, credentials: HTTPAuthorizationCredentials = HTTPAuthCredDep) -> str:
    """
    Dependency to verify the Bearer token is valid and present in the database.

    Raises a 401 Unauthorized if the token is missing or invalid.
    """
    token = credentials.credentials

    hashed_token = hash_bearer_token(token)
    if session.exec(select(ApiAuth).where(ApiAuth.token_hash == hashed_token)).first() is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token
