import datetime
import logging

from fastapi import APIRouter, Depends, status
from sqlmodel import select
from sqlmodel.sql.expression import SelectOfScalar

from app.database.models import Player, Whitelist
from app.deps import SessionDep, verify_bearer
from app.routes.player import get_player_by_ckey, get_player_by_discord
from app.schemas.whitelist import NewWhitelistCkey, NewWhitelistDiscord

logger = logging.getLogger("main-logger")


router = APIRouter(prefix="/whitelist", tags=["Whitelist"])

def select_only_active_whitelists(selection: SelectOfScalar[Whitelist]):
    return selection.where(
        Whitelist.valid).where(
        Whitelist.expiration_time > datetime.datetime.now()
    )


@router.get("/", status_code=status.HTTP_200_OK)
async def get_whitelists(session: SessionDep, active_only: bool = True) -> list[Whitelist]:
    selection = select(Whitelist)
    if active_only:
        selection = select_only_active_whitelists(selection)
    return session.exec(selection).all()


@router.put("/", status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_bearer)])
async def create_whitelist(session: SessionDep, new_whitelist: Whitelist) -> Whitelist:
    session.add(new_whitelist)
    session.commit()
    session.refresh(new_whitelist)
    logger.info("Created whitelist entry: %s", new_whitelist)
    return new_whitelist


@router.get("/{wl_type}", status_code=status.HTTP_200_OK)
async def get_whitelists_by_type(session: SessionDep, wl_type: str, active_only: bool = True) -> list[Whitelist]:
    selection = select(Whitelist).where(Whitelist.wl_type == wl_type)
    if active_only:
        selection = select_only_active_whitelists(selection)

    return session.exec(selection).all()


@router.get("/{wl_type}/ckeys", status_code=status.HTTP_200_OK, tags=["la stampella", "ckey"])
async def get_whitelisted_ckeys(session: SessionDep, wl_type: str, active_only: bool = True) -> list[str]:
    """
    Returns all the whitelisted ckeys by wl_type.
    """
    selection = select(Player.ckey).join(
        Whitelist, Whitelist.player_id == Player.id).where(Whitelist.wl_type == wl_type)
    if active_only:
        selection = select_only_active_whitelists(selection)
    return session.exec(selection).all()


@router.get("/{wl_type}/ckey", status_code=status.HTTP_200_OK, tags=["ckey"])
async def get_whitelists_by_ckey(session: SessionDep, wl_type: str, ckey: str, active_only: bool = True) -> list[Whitelist]:
    selection = select(Whitelist
                       ).join(Player, Player.id == Whitelist.player_id
                              ).where(Player.ckey == ckey
                                      ).where(Whitelist.wl_type == wl_type)
    if active_only:
        selection = select_only_active_whitelists(selection)
    return session.exec(selection).all()


@router.post("/{wl_type}/ckey", status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_bearer)], tags=["ckey"])
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


@router.get("/{wl_type}/discord", status_code=status.HTTP_200_OK, tags=["discord"])
async def get_whitelists_by_discord(session: SessionDep, wl_type: str, discord_id: str, active_only: bool = True) -> list[Whitelist]:
    selection = select(Whitelist).join(Player, Player.id == Whitelist.player_id).where(
        Player.discord_id == discord_id).where(Whitelist.wl_type == wl_type)
    if active_only:
        selection = select_only_active_whitelists(selection)
    return session.exec(selection).all()


@router.post("/{wl_type}/discord", status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_bearer)], tags=["discord"])
async def create_whitelist_by_discord(session: SessionDep, wl_type: str, new_whitelist: NewWhitelistDiscord) -> Whitelist:
    player = await get_player_by_discord(session, new_whitelist.player_discord_id)
    admin = await get_player_by_discord(session, new_whitelist.admin_discord_id)

    wl = Whitelist(
        player_id=player.id,
        admin_id=admin.id,
        wl_type=wl_type,
        expiration_time=datetime.datetime.now(
        ) + datetime.timedelta(days=new_whitelist.duration_days),
    )
    return await create_whitelist(session, wl)

@router.get("/{wl_type}/discords", status_code=status.HTTP_201_CREATED, tags=["la stampella", "discord"])
async def get_whitelisted_discord_ids(session: SessionDep, wl_type: str, active_only: bool = True) -> list[str]:
    selection = select(Player.discord_id).join(
        Whitelist, Whitelist.player_id == Player.id).where(Whitelist.wl_type == wl_type)
    if active_only:
        selection = select_only_active_whitelists(selection)
    return session.exec(selection).all()