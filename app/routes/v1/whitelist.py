import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, update
from sqlmodel import select
from sqlmodel.sql.expression import SelectOfScalar

from app.database.models import Player, Whitelist, WhitelistBan
from app.deps import BEARER_DEP_RESPONSES, SessionDep, verify_bearer
from app.routes.v1.player import get_player_by_discord_id
from app.schemas.generic import PaginatedResponse, paginate_selection
from app.schemas.whitelist import (NEW_WHITELIST_BAN_TYPES,
                                   NEW_WHITELIST_TYPES, WhitelistPatch,
                                   resolve_whitelist_type)

logger = logging.getLogger(__name__)

# region # Whitelists

whitelist_router = APIRouter(prefix="/whitelists", tags=["Whitelist"])


def select_only_active_whitelists(selection: SelectOfScalar[Whitelist]):
    return selection.where(
        Whitelist.valid).where(
        Whitelist.expiration_time > datetime.datetime.now()
    )


def filter_whitelists(selection: SelectOfScalar[Whitelist],
                      ckey: str | None = None,
                      discord_id: str | None = None,
                      admin_id: int | None = None,
                      server_type: str | None = None,
                      active_only: bool = True) -> SelectOfScalar[Whitelist]:
    if active_only:
        selection = select_only_active_whitelists(selection)
    if ckey is not None:
        selection = selection.where(Player.ckey == ckey)
    if discord_id is not None:
        selection = selection.where(Player.discord_id == discord_id)
    if admin_id is not None:
        selection = selection.where(Whitelist.admin_id == admin_id)
    if server_type is not None:
        selection = selection.where(Whitelist.server_type == server_type)
    return selection


def filter_whitelist_bans(selection: SelectOfScalar[WhitelistBan],
                          ckey: str | None = None,
                          discord_id: str | None = None,
                          server_type: str | None = None,
                          active_only: bool = True) -> SelectOfScalar[WhitelistBan]:
    if active_only:
        selection = select_only_active_whitelist_bans(selection)
    if ckey is not None:
        selection = selection.where(Player.ckey == ckey)
    if discord_id is not None:
        selection = selection.where(Player.discord_id == discord_id)
    if server_type is not None:
        selection = selection.where(WhitelistBan.server_type == server_type)
    return selection

# region Get


@whitelist_router.get("",
                      status_code=status.HTTP_200_OK,
                      responses={
                          status.HTTP_200_OK: {"description": "List of matching whitelists"},
                          status.HTTP_400_BAD_REQUEST: {"description": "Invalid filter combination"},
                      })
async def get_whitelists(session: SessionDep,
                         request: Request,
                         ckey: str | None = None,
                         discord_id: str | None = None,
                         admin_discord_id: str | None = None,
                         server_type: str | None = None,
                         active_only: bool = True,
                         page: int = 1,
                         page_size: int = 50) -> PaginatedResponse[Whitelist]:
    selection = select(Whitelist).join(
        Player, Player.id == Whitelist.player_id)  # type: ignore

    admin = await get_player_by_discord_id(session, admin_discord_id) if admin_discord_id is not None else None

    selection = filter_whitelists(
        selection, ckey, discord_id, admin.id if admin is not None else None, server_type, active_only)

    return paginate_selection(session, selection, request, page, page_size)


@whitelist_router.get("/ckeys",
                      status_code=status.HTTP_200_OK,
                      responses={
                          status.HTTP_200_OK: {"description": "Whitelisted ckeys"},
                      })
async def get_whitelisted_ckeys(session: SessionDep,
                                request: Request,
                                server_type: str | None = None,
                                active_only: bool = True,
                                page: int = 1,
                                page_size: int = 50) -> PaginatedResponse[str]:
    selection = select(Player.ckey).join(
        Whitelist, Player.id == Whitelist.player_id).where(Player.ckey != None).distinct()  # type: ignore

    selection = filter_whitelists(selection,
                                  server_type=server_type,
                                  active_only=active_only)

    return paginate_selection(session, selection, request, page, page_size)


@whitelist_router.get("/discord_ids",
                      status_code=status.HTTP_200_OK,
                      responses={
                          status.HTTP_200_OK: {"description": "Whitelisted discord ids"},
                      })
async def get_whitelisted_discord_ids(session: SessionDep,
                                      request: Request,
                                      server_type: str | None = None,
                                      active_only: bool = True,
                                      page: int = 1,
                                      page_size: int = 50) -> PaginatedResponse[str]:
    selection = select(Player.discord_id).join(
        Whitelist, Player.id == Whitelist.player_id).distinct()  # type: ignore

    selection = filter_whitelists(selection,
                                  server_type=server_type,
                                  active_only=active_only)

    return paginate_selection(session, selection, request, page, page_size)


@whitelist_router.get("/{id}",
                      status_code=status.HTTP_200_OK,
                      responses={
                          status.HTTP_200_OK: {"description": "Whitelist"},
                          status.HTTP_404_NOT_FOUND: {"description": "Whitelist not found"},
                      })
def get_whitelist(session: SessionDep,
                  id: int) -> Whitelist:  # pylint: disable=redefined-builtin
    wl = session.exec(select(Whitelist).where(Whitelist.id == id)).first()

    if wl is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Whitelist not found")

    return wl

# endregion
# region Post


WHITELIST_POST_RESPONSES = {
    **BEARER_DEP_RESPONSES,
    status.HTTP_201_CREATED: {"description": "Whitelist created"},
    status.HTTP_404_NOT_FOUND: {"description": "Player or admin not found"},
    status.HTTP_409_CONFLICT: {"description": "Player is banned from this type of whitelist."},
}


@whitelist_router.post("",
                       status_code=status.HTTP_201_CREATED,
                       responses=WHITELIST_POST_RESPONSES,
                       dependencies=[Depends(verify_bearer)])
async def create_whitelist(session: SessionDep, new_wl: NEW_WHITELIST_TYPES, ignore_bans: bool = False) -> Whitelist:
    player_resolver, admin_resolver = resolve_whitelist_type(new_wl)

    # TODO: wls only by discord and use `get_or_create_player_by_discord_id()`
    player = session.exec(select(Player).where(
        player_resolver(new_wl))).first()
    admin = session.exec(select(Player).where(admin_resolver(new_wl))).first()

    if player is None or admin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Player or admin not found")

    if not ignore_bans:
        selection = select(WhitelistBan).where(
            WhitelistBan.player_id == player.id).where(
            WhitelistBan.server_type == new_wl.server_type)
        selection = select_only_active_whitelist_bans(selection)

        if session.exec(selection).first() is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Player is banned from this type of whitelist.")

    wl = Whitelist(**new_wl.model_dump(),
                   expiration_time=datetime.datetime.now() + datetime.timedelta(days=new_wl.duration_days),
                   player_id=player.id,
                   admin_id=admin.id)
    session.add(wl)
    session.commit()
    session.refresh(wl)
    return wl


# endregion
# region Patch

WHITELIST_PATCH_RESPONSES = {
    **BEARER_DEP_RESPONSES,
    status.HTTP_200_OK: {"description": "Whitelist updated"},
    status.HTTP_404_NOT_FOUND: {"description": "Whitelist not found"},
}


@whitelist_router.patch("/{id}",
                        status_code=status.HTTP_200_OK,
                        responses=WHITELIST_PATCH_RESPONSES,
                        dependencies=[Depends(verify_bearer)])
async def update_whitelist(session: SessionDep, id: int, wl_patch: WhitelistPatch) -> Whitelist:  # pylint: disable=redefined-builtin
    wl = get_whitelist(session, id)
    update_data = wl_patch.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(wl, key, value)

    session.commit()
    session.refresh(wl)
    return wl

# endregion
# endregion
# region # WL Bans

whitelist_ban_router = APIRouter(
    prefix="/whitelist_bans", tags=["Whitelist Ban", "Ban", "Whitelist"])


def select_only_active_whitelist_bans(selection: SelectOfScalar[WhitelistBan]):
    return selection.where(
        WhitelistBan.valid).where(
        WhitelistBan.expiration_time > datetime.datetime.now()
    )


# region Get

@whitelist_ban_router.get("", status_code=status.HTTP_200_OK)
async def get_whitelist_bans(session: SessionDep,
                             request: Request,
                             ckey: str | None = None,
                             discord_id: str | None = None,
                             server_type: str | None = None,
                             active_only: bool = True,
                             page: int = 1,
                             page_size: int = 50) -> PaginatedResponse[WhitelistBan]:
    selection = select(WhitelistBan).join(
        Player, Player.id == WhitelistBan.player_id)  # type: ignore

    selection = filter_whitelist_bans(
        selection, ckey, discord_id, server_type, active_only)

    # type: ignore # pylint: disable=not-callable
    total = session.exec(selection.with_only_columns(func.count())).first()
    selection = selection.offset((page-1)*page_size).limit(page_size)
    items = session.exec(selection).all()

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        current_url=request.url,
    )


@whitelist_ban_router.get("/{id}",
                          status_code=status.HTTP_200_OK,
                          responses={
                              status.HTTP_200_OK: {"description": "Whitelist"},
                              status.HTTP_404_NOT_FOUND: {"description": "Whitelist not found"},
                          })
def get_whitelist_ban(session, id):  # pylint: disable=redefined-builtin
    wl_ban = session.exec(select(WhitelistBan).where(
        WhitelistBan.id == id)).first()

    if wl_ban is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Whitelist ban not found")

    return wl_ban

# endregion
# region Post


BAN_POST_RESPONSES = {
    **BEARER_DEP_RESPONSES,
    status.HTTP_201_CREATED: {"description": "Ban created"},
    status.HTTP_404_NOT_FOUND: {"description": "Player or admin not found"},
}


@whitelist_ban_router.post("",
                           status_code=status.HTTP_201_CREATED,
                           responses=BAN_POST_RESPONSES,
                           dependencies=[Depends(verify_bearer)])
async def create_whitelist_ban(session: SessionDep,
                               new_ban: NEW_WHITELIST_BAN_TYPES,
                               invalidate_wls: bool = True) -> WhitelistBan:
    player_resolver, admin_resolver = resolve_whitelist_type(new_ban)
    player = session.exec(select(Player).where(
        player_resolver(new_ban))).first()
    admin = session.exec(select(Player).where(admin_resolver(new_ban))).first()

    if player is None or admin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Player or admin not found")

    if invalidate_wls:
        session.exec(
            update(Whitelist).where(
                Whitelist.player_id == player.id
            ).where(
                Whitelist.server_type == new_ban.server_type
            ).where(
                Whitelist.expiration_time > datetime.datetime.now()
            ).values(
                valid=False
            )
        )

    ban = WhitelistBan(**new_ban.model_dump(),
                       player_id=player.id, admin_id=admin.id)
    session.add(ban)
    session.commit()
    session.refresh(ban)
    return ban

# endregion
# region Patch

WHITELIST_BAN_PATCH_RESPONSES = {
    **BEARER_DEP_RESPONSES,
    status.HTTP_200_OK: {"description": "Whitelist ban updated"},
    status.HTTP_404_NOT_FOUND: {"description": "Whitelist ban found"},
}


@whitelist_ban_router.patch("/{id}",
                            status_code=status.HTTP_200_OK,
                            responses=WHITELIST_PATCH_RESPONSES,
                            dependencies=[Depends(verify_bearer)])
async def update_whitelist_ban(session: SessionDep, id: int, wl_ban_patch: WhitelistPatch) -> WhitelistBan:  # pylint: disable=redefined-builtin
    ban = get_whitelist_ban(session, id)
    update_data = wl_ban_patch.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(ban, key, value)

    session.commit()
    session.refresh(ban)
    return ban


# endregion
# endregion
