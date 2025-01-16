import datetime
import logging

from fastapi import APIRouter, Depends, status
from sqlmodel import select
from sqlmodel.sql.expression import SelectOfScalar

from app.database.models import Player, Whitelist, WhitelistBan
from app.deps import SessionDep, verify_bearer
from app.routes.player import get_player_by_ckey, get_player_by_discord
from app.routes.whitelist import create_whitelist, select_only_active_whitelists
from app.schemas.whitelist import NewWhitelistCkey, NewWhitelistDiscord

router = APIRouter(prefix="/whitelistban", tags=["Whitelist", "Ban"])

@router.get("/", status_code=status.HTTP_200_OK)
async def get_whitelists_bans(session: SessionDep, active_only: bool = True) -> list[WhitelistBan]:
    selection = select(WhitelistBan)
    if active_only:
        selection = select_only_active_whitelists(selection)
    return session.exec(selection).all()

@router.post("/", status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_bearer)])
async def create_whitelist_ban(session: SessionDep, new_whitelist_ban: WhitelistBan) -> WhitelistBan:
    create_whitelist(session, new_whitelist_ban)
    return new_whitelist_ban

@router.get("/{wl_type}", status_code=status.HTTP_200_OK)
async def get_whitelists_bans_by_type(session: SessionDep, wl_type: str, active_only: bool = True) -> list[WhitelistBan]:
    selection = select(WhitelistBan).where(WhitelistBan.wl_type == wl_type)
    if active_only:
        selection = select_only_active_whitelists(selection)
    return session.exec(selection).all()

@router.get("/{wl_type}/ckey", status_code=status.HTTP_200_OK, tags=["la stampella", "ckey"])
async def get_whitelists_bans_by_ckey(session: SessionDep, wl_type: str, ckey: str, active_only: bool = True) -> list[WhitelistBan]:
    selection = select(WhitelistBan
                       ).join(Player, Player.id == WhitelistBan.player_id
                              ).where(Player.ckey == ckey
                                      ).where(WhitelistBan.wl_type == wl_type)
    if active_only:
        selection = select_only_active_whitelists(selection)
    return session.exec(selection).all()
