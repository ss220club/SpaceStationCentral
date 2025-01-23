import datetime
import logging

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import func
from sqlmodel import select
from sqlmodel.sql.expression import SelectOfScalar

from app.database.models import Player, Whitelist
from app.deps import SessionDep
from app.schemas.generic import PaginatedResponse

logger = logging.getLogger("main-logger")


router = APIRouter(prefix="/whitelists", tags=["Whitelist"])


def select_only_active_whitelists(selection: SelectOfScalar[Whitelist]):
    return selection.where(
        Whitelist.valid).where(
        Whitelist.expiration_time > datetime.datetime.now()
    )

@router.get("/",
            status_code=status.HTTP_200_OK,
            responses={
                status.HTTP_200_OK: {"description": "List of matching whitelists"},
                status.HTTP_400_BAD_REQUEST: {"description": "Invalid filter combination"},
            })
async def get_whitelists(session: SessionDep,
                         request: Request,
                         ckey: str = None,
                         discord_id: str = None,
                         wl_type: str = None,
                         active_only: bool = True,
                         page: int = 1,
                         page_size: int = 50) -> PaginatedResponse[Whitelist]:
    selection = select(Whitelist).join(
        Player, Player.id == Whitelist.player_id)

    if active_only:
        selection = select_only_active_whitelists(selection)
    if ckey is not None:
        selection = selection.where(Player.ckey == ckey)
    if discord_id is not None:
        selection = selection.where(Player.discord_id == discord_id)
    if wl_type is not None:
        selection = selection.where(Whitelist.type == wl_type)

    total = session.exec(select(func.count()).select_from(selection)).first()
    selection = selection.offset((page-1)*page_size).limit(page_size)
    items = session.exec(selection).all()


    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        current_url=request.url,
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_whitelist(session: SessionDep):
    pass

@router.post("/by-ckey", status_code=status.HTTP_201_CREATED)
async def create_whitelist_by_ckey(session: SessionDep):
    pass

@router.post("/by-discord", status_code=status.HTTP_201_CREATED)
async def create_whitelist_by_discord(session: SessionDep):
    pass