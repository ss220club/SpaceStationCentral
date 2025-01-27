import datetime
import logging
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlmodel import select
from sqlmodel.sql.expression import SelectOfScalar

from app.database.models import Player, Whitelist
from app.deps import BEARER_DEP_RESPONSES, SessionDep, verify_bearer
from app.schemas.generic import PaginatedResponse
from app.schemas.whitelist import (NewWhitelistBase, NewWhitelistCkey,
                                   NewWhitelistDiscord, NewWhitelistInternal)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whitelist", tags=["Whitelist"])
ban_router = APIRouter(prefix="/ban", tags=["Whitelist", "Ban"])


def select_only_active_whitelists(selection: SelectOfScalar[Whitelist]):
    return selection.where(
        Whitelist.valid).where(
        Whitelist.expiration_time > datetime.datetime.now()
    )

async def create_whitelist_helper(
    session: SessionDep,
    new_wl: NewWhitelistBase,
    player_resolver: Callable[[Any], SelectOfScalar[Player]],
    admin_resolver: Callable[[Any], SelectOfScalar[Player]],
) -> Whitelist:
    """Core logic for creating whitelist entries"""
    player = session.exec(select(Player).where(player_resolver(new_wl))).first()
    admin = session.exec(select(Player).where(admin_resolver(new_wl))).first()

    if not player or not admin:
        raise HTTPException(404, detail="Player or admin not found")

    wl = Whitelist(
        player_id=player.id,
        admin_id=admin.id,
        wl_type=new_wl.wl_type,
        expiration_time=new_wl.get_expiration_time(),
        valid=new_wl.valid
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

    total = session.exec(selection.with_only_columns(func.count())).first() # pylint: disable=not-callable
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
async def create_whitelist(session: SessionDep, new_wl: NewWhitelistInternal) -> Whitelist:
    return await create_whitelist_helper(
        session,
        new_wl,
        lambda d: Player.id == d.player_id,
        lambda d: Player.id == d.admin_id
    )


@router.post("/by-ckey", status_code=status.HTTP_201_CREATED, responses=WHITELIST_POST_RESPONSES, dependencies=[Depends(verify_bearer)])
async def create_whitelist_by_ckey(session: SessionDep, new_wl: NewWhitelistCkey) -> Whitelist:
    return await create_whitelist_helper(
        session,
        new_wl,
        lambda d: Player.ckey == d.player_ckey,
        lambda d: Player.ckey == d.admin_ckey
    )


@router.post("/by-discord", status_code=status.HTTP_201_CREATED, responses=WHITELIST_POST_RESPONSES, dependencies=[Depends(verify_bearer)])
async def create_whitelist_by_discord(session: SessionDep, new_wl: NewWhitelistDiscord) -> Whitelist:
    return await create_whitelist_helper(
        session,
        new_wl,
        lambda d: Player.discord_id == d.player_discord_id,
        lambda d: Player.discord_id == d.admin_discord_id
    )
