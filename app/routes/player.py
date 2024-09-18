import uuid
from fastapi import APIRouter, HTTPException
from fastapi import status

from app.database.models import CkeyToDiscord
from app.deps import SessionDep


router = APIRouter(prefix="/player", tags=["Player"], responses={404: {"description": "Not found"}})

