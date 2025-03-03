import hashlib
from typing import Annotated, Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from app.core.db import engine
from app.database.models import APIAuth


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]

bearer_scheme = HTTPBearer()


def hash_bearer_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


BEARER_DEP_RESPONSES = {
    status.HTTP_401_UNAUTHORIZED: {
        "description": "Invalid or missing bearer token",
    }
}


def verify_bearer(
    session: SessionDep,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    """
    Dependency to verify the Bearer token is valid and present in the database.
    Raises a 401 Unauthorized if the token is missing or invalid.
    """
    # Extract the token from the credentials
    token = credentials.credentials

    hashed_token = hash_bearer_token(token)
    if session.exec(
        select(APIAuth).where(APIAuth.token_hash == hashed_token)
    ).first() is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return token
