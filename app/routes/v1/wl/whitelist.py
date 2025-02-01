import datetime
import logging
from typing import Callable

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, update
from sqlmodel import select
from sqlmodel.sql.expression import SelectOfScalar

from app.database.models import Player, Whitelist, WhitelistBan
from app.deps import BEARER_DEP_RESPONSES, SessionDep, verify_bearer
from app.schemas.generic import PaginatedResponse
from app.schemas.whitelist import (NewWhitelistBanBase, NewWhitelistBanCkey,
                                   NewWhitelistBanDiscord, NewWhitelistBanInternal, NewWhitelistBase,
                                   NewWhitelistCkey, NewWhitelistDiscord,
                                   NewWhitelistInternal)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whitelist", tags=["Whitelist"])
ban_router = APIRouter(prefix="/ban", tags=["Whitelist", "Ban"])


def select_only_active_whitelists(selection: SelectOfScalar[Whitelist]):
    return selection.where(
        Whitelist.valid).where(
        Whitelist.expiration_time > datetime.datetime.now()
    )

WHITELIST_TYPES_T = NewWhitelistCkey | NewWhitelistDiscord | NewWhitelistInternal

async def create_whitelist_helper(
    session: SessionDep,
    new_wl: NewWhitelistBase,
    player_resolver: Callable[[WHITELIST_TYPES_T], bool],
    admin_resolver: Callable[[WHITELIST_TYPES_T], bool],
    ignore_bans: bool = False
) -> Whitelist:
    """Core logic for creating whitelist entries"""
    player: Player = session.exec(select(Player).where(player_resolver(new_wl))).first()
    admin: Player = session.exec(select(Player).where(admin_resolver(new_wl))).first()

    if not player or not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player or admin not found")

    if not ignore_bans and session.exec(
                select_only_active_whitelists(
                    select(WhitelistBan)
                    .where(WhitelistBan.player_id == player.id)
                    .where(WhitelistBan.wl_type == new_wl.wl_type)
                )
            ).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Player is banned from this type of whitelist.")

    wl = Whitelist(
        **new_wl.model_dump(),
        player_id=player.id,
        admin_id=admin.id,
        expiration_time=new_wl.get_expiration_time(),
    )

    session.add(wl)
    session.commit()
    session.refresh(wl)
    logger.info("Whitelist created: %s", wl.model_dump_json())
    return wl


@router.get("s/",  # /whitelists
            status_code=status.HTTP_200_OK,
            responses={
                status.HTTP_200_OK: {"description": "List of matching whitelists"},
                status.HTTP_400_BAD_REQUEST: {"description": "Invalid filter combination"},
            })
async def get_whitelists(session: SessionDep,
                         request: Request,
                         ckey: str | None = None,
                         discord_id: str | None = None,
                         wl_type: str | None = None,
                         active_only: bool = True,
                         page: int = 1,
                         page_size: int = 50) -> PaginatedResponse[Whitelist]:
    selection = select(Whitelist).join(
        Player, Player.id == Whitelist.player_id)  # type: ignore

    if active_only:
        selection = select_only_active_whitelists(selection)
    if ckey is not None:
        selection = selection.where(Player.ckey == ckey)
    if discord_id is not None:
        selection = selection.where(Player.discord_id == discord_id)
    if wl_type is not None:
        selection = selection.where(Whitelist.wl_type == wl_type)

    total = session.exec(selection.with_only_columns(func.count())).first() # type: ignore # pylint: disable=not-callable
    selection = selection.offset((page-1)*page_size).limit(page_size)
    items = session.exec(selection).all()

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        current_url=request.url,
    )

WHITELIST_POST_RESPONSES = {
    **BEARER_DEP_RESPONSES,
    status.HTTP_201_CREATED: {"description": "Whitelist created"},
    status.HTTP_404_NOT_FOUND: {"description": "Player or admin not found"},
    status.HTTP_409_CONFLICT: {"description": "Player is banned from this type of whitelist."},
}


@router.post("/", status_code=status.HTTP_201_CREATED, responses=WHITELIST_POST_RESPONSES, dependencies=[Depends(verify_bearer)])
async def create_whitelist(session: SessionDep, new_wl: NewWhitelistInternal, ignore_bans: bool = False) -> Whitelist:
    return await create_whitelist_helper(
        session,
        new_wl,
        lambda d: Player.id == d.player_id,
        lambda d: Player.id == d.admin_id,
        ignore_bans
    )


@router.post("/by-ckey", status_code=status.HTTP_201_CREATED, responses=WHITELIST_POST_RESPONSES, dependencies=[Depends(verify_bearer)])
async def create_whitelist_by_ckey(session: SessionDep, new_wl: NewWhitelistCkey, ignore_bans: bool = False) -> Whitelist:
    return await create_whitelist_helper(
        session,
        new_wl,
        lambda d: Player.ckey == d.player_ckey,
        lambda d: Player.ckey == d.admin_ckey,
        ignore_bans
    )


@router.post("/by-discord", status_code=status.HTTP_201_CREATED, responses=WHITELIST_POST_RESPONSES, dependencies=[Depends(verify_bearer)])
async def create_whitelist_by_discord(session: SessionDep, new_wl: NewWhitelistDiscord, ignore_bans: bool = False) -> Whitelist:
    return await create_whitelist_helper(
        session,
        new_wl,
        lambda d: Player.discord_id == d.player_discord_id,
        lambda d: Player.discord_id == d.admin_discord_id,
        ignore_bans
    )

BAN_POST_RESPONSES = {
    **BEARER_DEP_RESPONSES,
    status.HTTP_201_CREATED: {"description": "Ban created"},
    status.HTTP_404_NOT_FOUND: {"description": "Player or admin not found"},
}

def create_ban_helper(session: SessionDep,
                      new_ban: NewWhitelistBanBase,
                      player_resolver: Callable[[WHITELIST_TYPES_T], bool],
                      admin_resolver: Callable[[WHITELIST_TYPES_T], bool],
                      invalidate_wls: bool = True
                      ) -> WhitelistBan:
    player: Player = session.exec(select(Player).where(player_resolver(new_ban))).first()
    admin: Player = session.exec(select(Player).where(admin_resolver(new_ban))).first()

    if not player or not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player or admin not found")

    ban = WhitelistBan(**new_ban.model_dump(), player_id=player.id, admin_id=admin.id)
    session.add(ban)

    if invalidate_wls:
        session.exec(
            update(Whitelist)
            .where(Whitelist.player_id == player.id)
            .where(Whitelist.wl_type == new_ban.wl_type)
            .where(Whitelist.valid)
            .where(Whitelist.expiration_time > datetime.datetime.now())
            .values(valid=False)
        )

    session.commit()
    session.refresh(ban)
    logger.info("Whitelist ban created: %s", ban.model_dump_json())
    return ban

@ban_router.get("s/", status_code=status.HTTP_200_OK)
async def get_whitelist_bans(session: SessionDep,
                         request: Request,
                         ckey: str | None = None,
                         discord_id: str | None = None,
                         wl_type: str | None = None,
                         active_only: bool = True,
                         page: int = 1,
                         page_size: int = 50) -> PaginatedResponse[WhitelistBan]:
    selection = select(WhitelistBan).join(
        Player, Player.id == WhitelistBan.player_id)  # type: ignore

    if active_only:
        selection = select_only_active_whitelists(selection)
    if ckey is not None:
        selection = selection.where(Player.ckey == ckey)
    if discord_id is not None:
        selection = selection.where(Player.discord_id == discord_id)
    if wl_type is not None:
        selection = selection.where(WhitelistBan.wl_type == wl_type)

    total = session.exec(selection.with_only_columns(func.count())).first() # type: ignore # pylint: disable=not-callable
    selection = selection.offset((page-1)*page_size).limit(page_size)
    items = session.exec(selection).all()

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        current_url=request.url,
    )

@ban_router.post("/", status_code=status.HTTP_201_CREATED, responses=BAN_POST_RESPONSES, dependencies=[Depends(verify_bearer)])
async def create_whitelist_ban(session: SessionDep, new_ban: NewWhitelistBanInternal, invalidate_wls: bool = True) -> WhitelistBan:
    return create_ban_helper(
        session,
        new_ban,
        lambda d: Player.id == d.player_id,
        lambda d: Player.id == d.admin_id,
        invalidate_wls
    )

@ban_router.post("/by-ckey", status_code=status.HTTP_201_CREATED, responses=BAN_POST_RESPONSES, dependencies=[Depends(verify_bearer)])
async def create_whitelist_ban_by_ckey(session: SessionDep, new_ban: NewWhitelistBanCkey, invalidate_wls: bool = True) -> WhitelistBan:
    return create_ban_helper(
        session,
        new_ban,
        lambda d: Player.ckey == d.player_ckey,
        lambda d: Player.ckey == d.admin_ckey,
        invalidate_wls
    )

@ban_router.post("/by-discord", status_code=status.HTTP_201_CREATED, responses=BAN_POST_RESPONSES, dependencies=[Depends(verify_bearer)])
async def create_whitelist_ban_by_discord(session: SessionDep, new_ban: NewWhitelistBanDiscord, invalidate_wls: bool = True) -> WhitelistBan:
    return create_ban_helper(
        session,
        new_ban,
        lambda d: Player.discord_id == d.player_discord_id,
        lambda d: Player.discord_id == d.admin_discord_id,
        invalidate_wls
    )

router.include_router(ban_router)