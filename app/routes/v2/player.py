import app.database.crud.player as crud
from app.deps import SessionDep
from app.schemas.v2.player import PlayerNested
from fastapi import APIRouter, status


player_router = APIRouter(prefix="/players", tags=["Player"])


# region # Get
@player_router.get(
    "/discord/{discord_id}",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"description": "Player"},
        status.HTTP_404_NOT_FOUND: {"description": "Player not found"},
    },
)
async def get_player_by_discord_id(session: SessionDep, discord_id: str) -> PlayerNested:
    player = crud.get_player_by_discord_id(session, discord_id)
    return PlayerNested.model_validate(player)


@player_router.get(
    "/ckey/{ckey}",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"description": "Player"},
        status.HTTP_404_NOT_FOUND: {"description": "Player not found"},
    },
)
async def get_player_by_ckey(session: SessionDep, ckey: str) -> PlayerNested:
    player = crud.get_player_by_ckey(session, ckey)
    return PlayerNested.model_validate(player)


@player_router.get(
    "/{id}",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"description": "Player"},
        status.HTTP_404_NOT_FOUND: {"description": "Player not found"},
    },
)
async def get_player_by_id(session: SessionDep, id: int) -> PlayerNested:  # pylint: disable=redefined-builtin
    player = crud.get_player_by_id(session, id)
    return PlayerNested.model_validate(player)


# endregion

# TODO: Other v1 functions. Probably not needed due to java migration
