import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select

from app.database.models import Player, Whitelist, WhitelistBan
from app.deps import SessionDep, verify_bearer

logger = logging.getLogger("main-logger")


router = APIRouter(prefix="/whitelist", tags=["Whitelist"])


@router.post("/", dependencies=[Depends(verify_bearer)], status_code=status.HTTP_201_CREATED)
def create_whitelist(session: SessionDep, wl: Whitelist, ignore_bans: bool = False) -> Whitelist:
    if not ignore_bans:
        bans = session.exec(select(WhitelistBan).where(
            WhitelistBan.player_id == wl.player_id
            and WhitelistBan.valid == True
            and WhitelistBan.type == wl.type
            and WhitelistBan.issue_time + WhitelistBan.duration < wl.issue_time)).first()
        if bans is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Player is banned",
                            headers={"X-Retry-After": str(WhitelistBan.issue_time + WhitelistBan.duration)})

    session.add(wl)
    session.commit()
    session.refresh(wl)
    return wl


@router.get("/ckey/{ckey}", status_code=status.HTTP_200_OK)
async def get_whitelist_by_ckey(session: SessionDep, ckey: str, valid: bool = True) -> list[Whitelist]:
    result = session.exec(select(Whitelist).join(Player, onclause=Player.discord_id == Whitelist.player_id)
                          .where(Player.ckey == ckey and Whitelist.valid == valid))
    return result.all()

@router.get("/discord/{discord_id}", status_code=status.HTTP_200_OK)
async def get_whitelist_by_discord(session: SessionDep, discord_id: str, valid: bool = True) -> list[Whitelist]:
    result = session.exec(select(Whitelist).join(Player, onclause=Player.discord_id == Whitelist.player_id)
                          .where(Player.discord_id == discord_id and Whitelist.valid == valid))
    return result.all()

@router.post("/ban", dependencies=[Depends(verify_bearer)], status_code=status.HTTP_201_CREATED)
def ban_whitelist(session: SessionDep, wl: Whitelist, invalidate_old_wls: bool = True) -> WhitelistBan:
    ban = WhitelistBan(player_id=wl.player_id, type=wl.type, admin_id=wl.admin_id, duration=wl.duration)
    session.add(ban)
    if invalidate_old_wls:
        old_wls = session.exec(select(Whitelist).where(Whitelist.player_id == wl.player_id)).all()
        for old_wl in old_wls:
            old_wl.valid = False
        session.add_all(old_wls)

    session.commit()
    session.refresh(wl)
    return wl

@router.get("/ban/discord/{discord_id}", status_code=status.HTTP_200_OK)
async def get_whitelist_bans_by_discord(session: SessionDep, discord_id: str, only_active: bool = True) -> list[WhitelistBan]:
    result = session.exec(select(WhitelistBan).where(
        WhitelistBan.player_id == discord_id
        and WhitelistBan.valid == only_active
        and WhitelistBan.issue_time + WhitelistBan.duration > datetime.now()))
    return result.all()