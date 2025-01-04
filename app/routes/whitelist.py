import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select

from app.database.models import Player, Whitelist, WhitelistBan
from app.deps import SessionDep, verify_bearer
from app.schemas.whitelist import NewWhitelistBanCkey, NewWhitelistCkey

logger = logging.getLogger("main-logger")


router = APIRouter(prefix="/whitelist", tags=["Whitelist"])


def create_player_if_not_exists(session: SessionDep, discord_id: str) -> Player:
    player = session.exec(select(Player).where(
        Player.discord_id == discord_id)).first()
    if player is None:
        player = Player(discord_id=discord_id)
        session.add(player)
        session.commit()
        session.refresh(player)
    return player


@router.post("/", dependencies=[Depends(verify_bearer)], status_code=status.HTTP_201_CREATED)
async def create_whitelist(session: SessionDep, wl: Whitelist, ignore_bans: bool = False) -> Whitelist:
    create_player_if_not_exists(session, wl.player_id)

    if not ignore_bans:
        bans = session.exec(select(WhitelistBan).where(
            WhitelistBan.player_id == wl.player_id).where(
            WhitelistBan.valid is True).where(
            WhitelistBan.wl_type == wl.wl_type).where(
            WhitelistBan.issue_time + WhitelistBan.duration > wl.issue_time)).first()
        if bans is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Player is banned",
                                headers={"X-Retry-After": str(WhitelistBan.issue_time + WhitelistBan.duration)})

    session.add(wl)
    session.commit()
    session.refresh(wl)
    return wl


@router.get("/ckey/{ckey}", status_code=status.HTTP_200_OK)
async def get_whitelist_by_ckey(session: SessionDep, ckey: str, valid: bool = True, wl_type: str | None = None) -> list[Whitelist]:
    result = session.exec(select(Whitelist)
                          .join(Player, onclause=Player.discord_id == Whitelist.player_id)
                          .where(Player.ckey == ckey)
                          .where(Whitelist.valid == valid))
    if wl_type is not None:
        result = result.where(Whitelist.wl_type == wl_type)
    return result.all()


@router.post("/ckey", dependencies=[Depends(verify_bearer)], status_code=status.HTTP_201_CREATED)
async def create_whitelist_by_ckey(session: SessionDep, wl: NewWhitelistCkey, ignore_bans: bool = False) -> Whitelist:
    player = session.exec(select(Player).where(
        Player.ckey == wl.player_ckey)).first()
    if player is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")
    if not ignore_bans:
        bans = get_whitelist_bans_by_discord(session, player.discord_id)
        if bans is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Player is banned",
                                headers={"X-Retry-After": str(WhitelistBan.issue_time + WhitelistBan.duration)})
    admin = session.exec(select(Player).where(
        Player.ckey == wl.admin_ckey)).first()
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found")

    new_wl = Whitelist(**wl.model_dump(),
                       admin_id=admin.discord_id,
                       player_id=player.discord_id,
                       duration=datetime.timedelta(days=wl.duration_days))
    session.add(new_wl)
    session.commit()
    session.refresh(new_wl)
    return new_wl


@router.get("/discord/{discord_id}", status_code=status.HTTP_200_OK)
async def get_whitelist_by_discord(session: SessionDep, discord_id: str, valid: bool = True, wl_type: str | None = None) -> list[Whitelist]:
    result = session.exec(select(Whitelist)
                          .join(Player, onclause=Player.discord_id == Whitelist.player_id)
                          .where(Player.discord_id == discord_id)
                          .where(Whitelist.valid == valid))
    if wl_type is not None:
        result = result.where(Whitelist.wl_type == wl_type)
    return result.all()


@router.post("/ban", dependencies=[Depends(verify_bearer)], status_code=status.HTTP_201_CREATED)
async def ban_whitelist(session: SessionDep, ban: WhitelistBan, invalidate_old_wls: bool = True) -> WhitelistBan:
    create_player_if_not_exists(session, ban.player_id)

    session.add(ban)
    if invalidate_old_wls:
        old_wls = session.exec(select(Whitelist)
                               .where(Whitelist.player_id == ban.player_id).
                               where(Whitelist.wl_type == ban.wl_type)
                               ).all()
        for old_wl in old_wls:
            old_wl.valid = False
        session.add_all(old_wls)

    session.commit()
    session.refresh(ban)
    return ban


@router.post("/ban/ckey", dependencies=[Depends(verify_bearer)], status_code=status.HTTP_201_CREATED)
async def ban_whitelist_by_ckey(session: SessionDep, ban: NewWhitelistBanCkey, invalidate_old_wls: bool = True) -> WhitelistBan:
    player = session.exec(select(Player).where(
        Player.ckey == ban.player_ckey)).first()
    if player is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")
    admin = session.exec(select(Player).where(
        Player.ckey == ban.admin_ckey)).first()
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found")
    return await ban_whitelist(session, WhitelistBan(**ban.model_dump(), player_id=player.discord_id, admin_id=admin.discord_id, duration=datetime.timedelta(days=ban.duration_days)), invalidate_old_wls)


@router.get("/ban/discord/{discord_id}", status_code=status.HTTP_200_OK)
async def get_whitelist_bans_by_discord(session: SessionDep, discord_id: str, wl_type: str | None = None, only_active: bool = True) -> list[WhitelistBan]:
    result = session.exec(select(WhitelistBan).where(
        WhitelistBan.player_id == discord_id).where(
        WhitelistBan.valid == only_active).where(
        WhitelistBan.issue_time + WhitelistBan.duration > datetime.datetime.now()))
    if wl_type is not None:
        result = result.where(WhitelistBan.wl_type == wl_type)
    return result.all()


@router.patch("/ban", dependencies=[Depends(verify_bearer)], status_code=status.HTTP_202_ACCEPTED)
async def pardon_whitelist_ban(session: SessionDep, ban_id: int) -> WhitelistBan:
    db_ban = session.exec(select(WhitelistBan).where(
        WhitelistBan.id == ban_id)).first()
    if db_ban is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ban not found")
    db_ban.valid = False
    session.add(db_ban)
    session.commit()
    session.refresh(db_ban)
    return db_ban


@router.get("/simple/is_whitelisted/ckey/{ckey}", status_code=status.HTTP_200_OK)
async def is_whitelisted(session: SessionDep, ckey: str, wl_type: str) -> bool:
    return session.exec(select(Whitelist)
                        .join(Player, onclause=Player.discord_id == Whitelist.player_id)
                        .where(Player.ckey == ckey)
                        .where(Whitelist.wl_type == wl_type)
                        .where(Whitelist.issue_time + Whitelist.duration > datetime.datetime.now())
                        .where(Whitelist.valid)).first() is not None


@router.get("/simple/active_whitelists/ckey", status_code=status.HTTP_200_OK)
async def active_whitelists(session: SessionDep, wl_type: str) -> list[str]:
    wls = session.exec(select(Player)
                       .join(Whitelist, onclause=Player.discord_id == Whitelist.player_id)
                       .where(Whitelist.wl_type == wl_type)
                       .where(Whitelist.issue_time + Whitelist.duration > datetime.datetime.now())
                       .where(Whitelist.valid)
                       ).all()
    return [wl.ckey for wl in wls]
