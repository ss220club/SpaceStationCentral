import hashlib
from typing import Annotated, Generator
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from app.core.db import engine
from app.database.models import Auth

def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]

bearer_scheme = HTTPBearer()
def verify_bearer_in_db(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: Session = Depends(get_session),
) -> str:
    """
    Dependency to verify the Bearer token is valid and present in the database.
    Raises a 401 Unauthorized if the token is missing or invalid.
    """
    # Extract the token from the credentials
    token = credentials.credentials

    hashed_token = hashlib.sha256(token.encode()).hexdigest()
    token_entry = session.exec(select(Auth).where(Auth.token_hash == hashed_token)).first()

    if not token_entry:
        raise HTTPException(
            status_code=401, 
            detail="Invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return token

BearerDep = Annotated[str, Depends(verify_bearer_in_db)]