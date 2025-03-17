import logging
from datetime import UTC, datetime
from operator import eq, gt, ne
from typing import TypeVar, cast

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import func, select, update
from sqlmodel.sql.expression import Select

from app.database.models import Player, Whitelist, WhitelistBan
from app.deps import AUTH_RESPONSES, SessionDep, verify_bearer
from app.routes.v1.player import get_player_by_discord_id
from app.schemas.generic import PaginatedResponse, paginate_selection
from app.schemas.whitelist import NewWhitelist, NewWhitelistBan, WhitelistPatch


logger = logging.getLogger(__name__)
T = TypeVar("T")

# region # Whitelists

whitelist_router = APIRouter(prefix="/whitelists", tags=["Whitelist"])


def __filter_whitelists(
    selection: Select[tuple[T, ...]],
    ckey: str | None = None,
    discord_id: str | None = None,
    admin_id: int | None = None,
    server_type: str | None = None,
    active_only: bool = True,
) -> Select[tuple[T, ...]]:
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


def select_only_active_whitelists(selection: Select[tuple[T, ...]]) -> Select[tuple[T, ...]]:
    return selection.where(Whitelist.valid).where(Whitelist.expiration_time > datetime.now(UTC))


# region Get


@whitelist_router.get(
    "",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"description": "List of matching whitelists"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid filter combination"},
    },
)
async def get_whitelists(
    session: SessionDep,
    request: Request,
    ckey: str | None = None,
    discord_id: str | None = None,
    admin_discord_id: str | None = None,
    server_type: str | None = None,
    active_only: bool = True,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedResponse[Whitelist]:
    selection = cast(Select[tuple[Whitelist]], select(Whitelist).join(Player))  # pyright: ignore[reportInvalidCast]
    admin = await get_player_by_discord_id(session, admin_discord_id) if admin_discord_id is not None else None
    selection = __filter_whitelists(selection, ckey, discord_id, admin and admin.id, server_type, active_only)

    return paginate_selection(session, selection, request, page, page_size)


@whitelist_router.get(
    "/ckeys",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"description": "Whitelisted ckeys"},
    },
)
async def get_whitelisted_ckeys(
    session: SessionDep,
    request: Request,
    server_type: str | None = None,
    active_only: bool = True,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedResponse[str]:
    selection = cast(Select[tuple[str]], select(Player.ckey).join(Whitelist).where(ne(Player.ckey, None)).distinct())  # pyright: ignore[reportInvalidCast]
    selection = __filter_whitelists(selection, server_type=server_type, active_only=active_only)

    return paginate_selection(session, selection, request, page, page_size)


@whitelist_router.get(
    "/discord_ids",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"description": "Whitelisted discord ids"},
    },
)
async def get_whitelisted_discord_ids(
    session: SessionDep,
    request: Request,
    server_type: str | None = None,
    active_only: bool = True,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedResponse[str]:
    selection = cast(Select[tuple[str]], select(Player.discord_id).join(Whitelist).distinct())  # pyright: ignore[reportInvalidCast]
    selection = __filter_whitelists(selection, server_type=server_type, active_only=active_only)

    return paginate_selection(session, selection, request, page, page_size)


@whitelist_router.get(
    "/{id}",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"description": "Whitelist"},
        status.HTTP_404_NOT_FOUND: {"description": "Whitelist not found"},
    },
)
def get_whitelist(session: SessionDep, id: int) -> Whitelist:
    wl = session.exec(select(Whitelist).where(Whitelist.id == id)).first()

    if wl is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Whitelist not found")

    return wl


# endregion
# region Post


WHITELIST_POST_RESPONSES = {
    **AUTH_RESPONSES,
    status.HTTP_201_CREATED: {"description": "Whitelist created"},
    status.HTTP_404_NOT_FOUND: {"description": "Player or admin not found"},
    status.HTTP_409_CONFLICT: {"description": "Player is banned from this type of whitelist."},
}


@whitelist_router.post(
    "", status_code=status.HTTP_201_CREATED, responses=WHITELIST_POST_RESPONSES, dependencies=[Depends(verify_bearer)]
)
async def create_whitelist(session: SessionDep, new_wl: NewWhitelist, ignore_bans: bool = False) -> Whitelist:
    # TODO: wls only by discord and use `get_or_create_player_by_discord_id()`
    player = session.exec(select(Player).where(new_wl.get_player_clause())).first()
    admin = session.exec(select(Player).where(new_wl.get_admin_clause())).first()

    if player is None or admin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player or admin not found")

    if not ignore_bans:
        selection = cast(
            Select[tuple[WhitelistBan]],
            (
                select(WhitelistBan)
                .where(WhitelistBan.player_id == player.id)
                .where(WhitelistBan.server_type == new_wl.server_type)
            ),  # pyright: ignore[reportInvalidCast]
        )
        selection = select_only_active_whitelist_bans(selection)

        if session.exec(selection).first() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Player is banned from this type of whitelist."
            )

    wl = Whitelist(
        **new_wl.model_dump(),
        expiration_time=new_wl.get_expiration_time(),
        player_id=player.id,  # pyright: ignore[reportArgumentType]
        admin_id=admin.id,  # pyright: ignore[reportArgumentType]
    )
    session.add(wl)
    session.commit()
    session.refresh(wl)
    logging.info("Whitelist created: %s", wl.model_dump_json())
    return wl


# endregion
# region Patch

WHITELIST_PATCH_RESPONSES = {
    **AUTH_RESPONSES,
    status.HTTP_200_OK: {"description": "Whitelist updated"},
    status.HTTP_404_NOT_FOUND: {"description": "Whitelist not found"},
}


@whitelist_router.patch(
    "/{id}", status_code=status.HTTP_200_OK, responses=WHITELIST_PATCH_RESPONSES, dependencies=[Depends(verify_bearer)]
)
async def update_whitelist(session: SessionDep, id: int, wl_patch: WhitelistPatch) -> Whitelist:  # pylint: disable=redefined-builtin
    wl = get_whitelist(session, id)
    update_data = wl_patch.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(wl, key, value)

    session.commit()
    session.refresh(wl)
    logger.info("Whitelist updated: %s", wl.model_dump_json())
    return wl


# endregion
# endregion
# region # WL Bans

whitelist_ban_router = APIRouter(prefix="/whitelist_bans", tags=["Whitelist Ban", "Ban", "Whitelist"])


def filter_whitelist_bans(
    selection: Select[T],
    ckey: str | None = None,
    discord_id: str | None = None,
    admin_id: int | None = None,
    server_type: str | None = None,
    active_only: bool = True,
) -> Select[T]:
    if active_only:
        selection = select_only_active_whitelist_bans(selection)
    if ckey is not None:
        selection = selection.where(Player.ckey == ckey)
    if discord_id is not None:
        selection = selection.where(Player.discord_id == discord_id)
    if admin_id is not None:
        selection = selection.where(WhitelistBan.admin_id == admin_id)
    if server_type is not None:
        selection = selection.where(WhitelistBan.server_type == server_type)
    return selection


def select_only_active_whitelist_bans(selection: Select[T]) -> Select[T]:
    return selection.where(WhitelistBan.valid).where(WhitelistBan.expiration_time > datetime.now(UTC))


# region Get


@whitelist_ban_router.get("", status_code=status.HTTP_200_OK)
async def get_whitelist_bans(
    session: SessionDep,
    request: Request,
    ckey: str | None = None,
    discord_id: str | None = None,
    admin_discord_id: str | None = None,
    server_type: str | None = None,
    active_only: bool = True,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedResponse[WhitelistBan]:
    selection = cast(Select[tuple[WhitelistBan]], select(WhitelistBan).join(Player))  # pyright: ignore[reportInvalidCast]

    admin = await get_player_by_discord_id(session, admin_discord_id) if admin_discord_id is not None else None

    selection = filter_whitelist_bans(selection, ckey, discord_id, admin and admin.id, server_type, active_only)
    total = session.exec(select(func.count()).select_from(selection.subquery())).one()
    selection = selection.offset((page - 1) * page_size).limit(page_size)
    items = session.exec(selection).all()

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        current_url=request.url,
    )


@whitelist_ban_router.get(
    "/{id}",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"description": "Whitelist"},
        status.HTTP_404_NOT_FOUND: {"description": "Whitelist not found"},
    },
)
async def get_whitelist_ban(session: SessionDep, id: int) -> WhitelistBan:
    wl_ban = session.exec(select(WhitelistBan).where(WhitelistBan.id == id)).first()

    if wl_ban is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Whitelist ban not found")

    return wl_ban


# endregion
# region Post


BAN_POST_RESPONSES = {
    **AUTH_RESPONSES,
    status.HTTP_201_CREATED: {"description": "Ban created"},
    status.HTTP_404_NOT_FOUND: {"description": "Player or admin not found"},
}


@whitelist_ban_router.post(
    "", status_code=status.HTTP_201_CREATED, responses=BAN_POST_RESPONSES, dependencies=[Depends(verify_bearer)]
)
async def create_whitelist_ban(
    session: SessionDep, new_ban: NewWhitelistBan, invalidate_wls: bool = True
) -> WhitelistBan:
    player = session.exec(select(Player).where(new_ban.get_player_clause())).first()
    admin = session.exec(select(Player).where(new_ban.get_admin_clause())).first()

    if player is None or admin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player or admin not found")

    if invalidate_wls:
        query = (
            update(Whitelist)
            .values(valid=False)
            .where(eq(Whitelist.player_id, player.id))
            .where(eq(Whitelist.server_type, new_ban.server_type))
            .where(gt(Whitelist.expiration_time, datetime.now(UTC)))
        )
        session.execute(query)  # pyright: ignore[reportDeprecated]

    ban = WhitelistBan(
        **new_ban.model_dump(),
        expiration_time=new_ban.get_expiration_time(),
        player_id=player.id,  # pyright: ignore[reportArgumentType]
        admin_id=admin.id,  # pyright: ignore[reportArgumentType]
    )
    session.add(ban)
    session.commit()
    session.refresh(ban)
    logging.info("Whitelist ban created: %s", ban.model_dump_json())
    return ban


# endregion
# region Patch

WHITELIST_BAN_PATCH_RESPONSES = {
    **AUTH_RESPONSES,
    status.HTTP_200_OK: {"description": "Whitelist ban updated"},
    status.HTTP_404_NOT_FOUND: {"description": "Whitelist ban found"},
}


@whitelist_ban_router.patch(
    "/{id}",
    status_code=status.HTTP_200_OK,
    responses=WHITELIST_BAN_PATCH_RESPONSES,
    dependencies=[Depends(verify_bearer)],
)
async def update_whitelist_ban(session: SessionDep, id: int, wl_ban_patch: WhitelistPatch) -> WhitelistBan:
    ban = await get_whitelist_ban(session, id)

    update_data = wl_ban_patch.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(ban, key, value)

    session.commit()
    session.refresh(ban)
    logging.info("Whitelist ban updated: %s", ban.model_dump_json())
    return ban


# endregion
# endregion
