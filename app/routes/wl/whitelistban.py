import datetime
import logging

from fastapi import APIRouter, Depends, status
from sqlmodel import select

from app.database.models import Player, Whitelist, WhitelistBan
from app.deps import BEARER_DEP_RESPONSES, SessionDep, verify_bearer
from app.routes.player import get_player_by_ckey, get_player_by_discord
from app.routes.wl.whitelist import create_whitelist, select_only_active_whitelists
from app.schemas.whitelist import NewWhitelistBanCkey, NewWhitelistBanDiscord

logger = logging.getLogger("main-logger")


router = APIRouter(prefix="/whitelistban", tags=["Whitelist", "WhitelistBan"])


@router.get("/", status_code=status.HTTP_200_OK)
async def get_whitelistbans(session: SessionDep, active_only: bool = True) -> list[WhitelistBan]:
    selection = select(WhitelistBan)
    if active_only:
        selection = select_only_active_whitelists(selection)
    return session.exec(selection).all()


@router.get("/{wl_type}", status_code=status.HTTP_200_OK)
async def get_whitelistbans_by_type(session: SessionDep, wl_type: str, active_only: bool = True) -> list[WhitelistBan]:
    selection = select(WhitelistBan).where(WhitelistBan.wl_type == wl_type)
    if active_only:
        selection = select_only_active_whitelists(selection)
    return session.exec(selection).all()


@router.get("/{wl_type}/ckey", status_code=status.HTTP_200_OK, tags=["ckey"])
async def get_whitelistbans_by_ckey(session: SessionDep, wl_type: str, ckey: str, active_only: bool = True) -> list[WhitelistBan]:
    selection = select(WhitelistBan
                       ).join(Player, Player.id == WhitelistBan.player_id
                              ).where(Player.ckey == ckey
                                      ).where(WhitelistBan.wl_type == wl_type)
    if active_only:
        selection = select_only_active_whitelists(selection)
    return session.exec(selection).all()


@router.get("/{wl_type}/discord", status_code=status.HTTP_200_OK, tags=["discord"])
async def get_whitelistbans_by_discord(session: SessionDep, wl_type: str, discord_id: str, active_only: bool = True) -> list[WhitelistBan]:
    selection = select(WhitelistBan
                       ).join(Player, Player.id == WhitelistBan.player_id
                              ).where(Player.discord_id == discord_id
                                      ).where(WhitelistBan.wl_type == wl_type)
    if active_only:
        selection = select_only_active_whitelists(selection)
    return session.exec(selection).all()


@router.post("/{wl_type}/ckey", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(verify_bearer)], responses=BEARER_DEP_RESPONSES, tags=["ckey"])
async def create_whitelist_by_ckey(session: SessionDep, wl_type: str, ckey: str, new_whitelist: NewWhitelistBanCkey) -> Whitelist:
    player = await get_player_by_ckey(session, ckey)
    admin = await get_player_by_ckey(session, new_whitelist.admin_ckey)
    wl = WhitelistBan(
        player_id=player.id,
        admin_id=admin.id,
        wl_type=wl_type,
        expiration_time=datetime.datetime.now(
        ) + datetime.timedelta(days=new_whitelist.duration_days),
        reason=new_whitelist.reason
    )
    return await create_whitelist(session, wl, ignore_bans=True)


@router.get("/{wl_type}/discord", status_code=status.HTTP_200_OK, tags=["discord"])
async def get_whitelists_by_discord(session: SessionDep, wl_type: str, discord_id: str, active_only: bool = True) -> list[Whitelist]:
    selection = select(Whitelist).join(Player, Player.id == Whitelist.player_id).where(
        Player.discord_id == discord_id).where(Whitelist.wl_type == wl_type)
    if active_only:
        selection = select_only_active_whitelists(selection)
    return session.exec(selection).all()


@router.post("/{wl_type}/discord", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(verify_bearer)], responses=BEARER_DEP_RESPONSES, tags=["discord"])
async def create_whitelist_by_discord(session: SessionDep, wl_type: str, new_whitelist: NewWhitelistBanDiscord) -> Whitelist:
    player = await get_player_by_discord(session, new_whitelist.player_discord_id)
    admin = await get_player_by_discord(session, new_whitelist.admin_discord_id)

    wl = WhitelistBan(
        player_id=player.id,
        admin_id=admin.id,
        wl_type=wl_type,
        expiration_time=datetime.datetime.now(
        ) + datetime.timedelta(days=new_whitelist.duration_days),
        reason=new_whitelist.reason
    )
    return await create_whitelist(session, wl, ignore_bans=True)


@router.get("/{wl_type}/discords", status_code=status.HTTP_201_CREATED, tags=["la stampella", "discord"])
async def get_whitelisted_discord_ids(session: SessionDep, wl_type: str, active_only: bool = True) -> list[str]:
    selection = select(Player.discord_id).join(
        Whitelist, Whitelist.player_id == Player.id).where(Whitelist.wl_type == wl_type)
    if active_only:
        selection = select_only_active_whitelists(selection)
    return session.exec(selection).all()
