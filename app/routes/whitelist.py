import datetime
import logging

from fastapi import APIRouter, Depends, status
from sqlmodel import select

from app.database.models import Player, Whitelist
from app.deps import SessionDep, verify_bearer
from app.routes.player import get_player_by_ckey, get_player_by_discord
from app.schemas.whitelist import NewWhitelistCkey, NewWhitelistDiscord

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


@router.post("/", dependencies=[Depends(verify_bearer)])
async def create_whitelist(session: SessionDep, new_whitelist: Whitelist) -> Whitelist:
    session.add(new_whitelist)
    session.commit()
    session.refresh(new_whitelist)
    logger.info("Created whitelist: %s", new_whitelist)
    return new_whitelist


@router.get("/{wl_type}/ckey/{ckey}", status_code=status.HTTP_200_OK)
async def get_whitelists_by_ckey(session: SessionDep, wl_type: str, ckey: str, active_only: bool = True) -> list[Whitelist]:
    selection = select(Whitelist
                       ).join(Player, Player.id == Whitelist.player_id
                              ).where(Player.ckey == ckey
                                      ).where(Whitelist.wl_type == wl_type)
    if active_only:
        selection = selection.where(
            Whitelist.valid).where(
            Whitelist.expiration_time > datetime.datetime.now()
        )
    return session.exec(selection).all()


@router.post("/{wl_type}/ckey/{ckey}", dependencies=[Depends(verify_bearer)])
async def create_whitelist_by_ckey(session: SessionDep, wl_type: str, ckey: str, new_whitelist: NewWhitelistCkey) -> Whitelist:
    player = await get_player_by_ckey(session, ckey)
    admin = await get_player_by_ckey(session, new_whitelist.admin_ckey)

    wl = Whitelist(
        player_id=player.id,
        admin_id=admin.id,
        wl_type=wl_type,
        expiration_time=datetime.datetime.now(
        ) + datetime.timedelta(days=new_whitelist.duration_days),
        valid=new_whitelist.valid
    )
    return await create_whitelist(session, wl)


@router.get("/{wl_type}/discord/{discord_id}", status_code=status.HTTP_200_OK)
async def get_whitelists_by_discord(session: SessionDep, wl_type: str, discord_id: str, active_only: bool = True) -> list[Whitelist]:
    selection = select(Whitelist).join(Player, Player.id == Whitelist.player_id).where(
        Player.discord_id == discord_id).where(Whitelist.wl_type == wl_type)
    if active_only:
        selection = selection.where(
            Whitelist.valid).where(
            Whitelist.expiration_time > datetime.datetime.now()
        )
    return session.exec(selection).all()


@router.post("/{wl_type}/discord/{discord_id}", dependencies=[Depends(verify_bearer)])
async def create_whitelist_by_discord(session: SessionDep, new_whitelist: NewWhitelistDiscord) -> Whitelist:
    player = await get_player_by_discord(session, new_whitelist.discord_id)
    admin = await get_player_by_ckey(session, new_whitelist.admin_ckey)

    wl = Whitelist(
        player_id=player.id,
        admin_id=admin.id,
        wl_type=new_whitelist.wl_type,
        expiration_time=datetime.datetime.now(
        ) + datetime.timedelta(days=new_whitelist.duration_days),
        valid=new_whitelist.valid
    )
    return await create_whitelist(session, wl)

router.include_router(whitelist_ban_router)
