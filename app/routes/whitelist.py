import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select

from app.database.models import Player, Whitelist, WhitelistBan
from app.deps import SessionDep, verify_bearer
from app.schemas.whitelist import NewWhitelistBanCkey, NewWhitelistCkey

logger = logging.getLogger("main-logger")


router = APIRouter(prefix="/whitelist", tags=["Whitelist"])
whitelist_ban_router = APIRouter(prefix="/ban", tags=["WhitelistBan", "Ban"])


@router.get("/", status_code=status.HTTP_200_OK)
async def get_whitelists(session: SessionDep, active_only: bool = True) -> list[Whitelist]:
    selection = select(Whitelist)
    if active_only:
        selection = selection.where(
            Whitelist.valid).where(
            Whitelist.expiration_time > datetime.datetime.now()
        )
    return session.exec(selection).all()
