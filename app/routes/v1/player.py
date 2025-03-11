import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlmodel import Session, func, select

from app.core import redis
from app.core.config import CONFIG
from app.database.models import CkeyLinkToken, Player
from app.deps import AUTH_RESPONSES, SessionDep, verify_bearer
from app.fur_discord import DiscordOAuthClient
from app.schemas.generic import PaginatedResponse
from app.schemas.player import NewPlayer, PlayerPatch


logger = logging.getLogger(__name__)

# region # OAuth

oauth_router = APIRouter(prefix="/oauth", tags=["OAuth"])

CALLBACK_PATH = "/discord_oa"
oauth_client = DiscordOAuthClient(
    CONFIG.oauth.client_id, CONFIG.oauth.client_secret, f"{CONFIG.oauth.endpoint_url}{CALLBACK_PATH}"
)


async def get_token_by_ckey(session: Session, ckey: str) -> str:
    """
    Get or generate a token for the given player ckey.

    If token doesn't exist - generates a new one.
    If token already exists, makes sure that it is still valid, if not - regenerates it.
    """
    token_entry = session.exec(select(CkeyLinkToken).where(CkeyLinkToken.ckey == ckey)).first()
    if token_entry is None:
        token_entry = CkeyLinkToken(ckey=ckey)
    elif token_entry.expiration_time < datetime.now(UTC):
        session.delete(token_entry)
        session.commit()
        token_entry = CkeyLinkToken(ckey=ckey)
    else:
        return token_entry.token

    session.add(token_entry)
    session.commit()
    session.refresh(token_entry)

    return token_entry.token


@oauth_router.get("/login", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
async def login(token: str) -> RedirectResponse:
    """Redirects to the discord oauth2 login page with the given ckey and state token."""
    return RedirectResponse(oauth_client.get_oauth_login_url(token))


@oauth_router.post(
    "/token", status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_bearer)], responses=AUTH_RESPONSES
)
async def generate_state(session: SessionDep, ckey: str) -> str:
    """
    Generate a state token for the given ckey and returns it.

    The state token is used to validate the authorization flow.
    """
    return await get_token_by_ckey(session, ckey)


@oauth_router.get(CALLBACK_PATH)
async def callback(session: SessionDep, code: str, state: str) -> Player:
    """
    The callback endpoint for the discord oauth2 flow.

    It takes the code and state parameters and verifies the state token.

    If the state token is invalid, it raises a 401 Unauthorized response.

    If the state token is valid, it uses the code to get an access token for the discord user.
    It then checks if the player is already linked with the discord user.

    If the player is already linked, it raises a 409 Conflict response.

    If the player is not already linked, it creates a new Player object with the ckey and discord_id
    and adds it to the database. It then returns the newly created Player object.
    """
    discord_token, _ = await oauth_client.get_access_token(code)
    if discord_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not get discord token")

    token_string = state
    token = session.exec(
        select(CkeyLinkToken)
        .where(CkeyLinkToken.token == token_string)
        .where(CkeyLinkToken.expiration_time > datetime.now(UTC))
    ).first()
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong or expired token")

    ckey = token.ckey
    discord_user = await oauth_client.get_user(discord_token)
    discord_id = discord_user.id

    if link := session.exec(select(Player).where(Player.discord_id == discord_id)).first():
        # General player account already exists
        if link.ckey is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Player already linked")

        logger.debug("Linking a preexisting player %s to %s", link.discord_id, ckey)
        link.ckey = ckey
    else:
        link = Player(ckey=ckey, discord_id=discord_id)

    session.add(link)
    session.delete(token)
    session.commit()
    session.refresh(link)

    logger.info("Linked %s to %s", link.ckey, link.discord_id)

    await update_player_event(link)

    return link


# endregion
# region # Players

player_router = APIRouter(prefix="/players", tags=["Player"])


async def get_or_create_player_by_discord_id(session: SessionDep, discord_id: str) -> Player:
    result = session.exec(select(Player).where(Player.discord_id == discord_id)).first()

    if result is None:
        player = Player(discord_id=discord_id, ckey=None)
        session.add(player)
        session.commit()
        session.refresh(player)
        return player

    return result


@player_router.get(
    "/discord/{discord_id}",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"description": "Player"},
        status.HTTP_404_NOT_FOUND: {"description": "Player not found"},
    },
)
async def get_player_by_discord_id(session: SessionDep, discord_id: str) -> Player:
    result = session.exec(select(Player).where(Player.discord_id == discord_id)).first()

    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")

    return result


@player_router.get(
    "/ckey/{ckey}",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"description": "Player"},
        status.HTTP_404_NOT_FOUND: {"description": "Player not found"},
    },
)
async def get_player_by_ckey(session: SessionDep, ckey: str) -> Player:
    result = session.exec(select(Player).where(Player.ckey == ckey)).first()

    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")

    return result


@player_router.get("", status_code=status.HTTP_200_OK)
async def get_players(
    session: SessionDep, request: Request, page: int = 1, page_size: int = 50
) -> PaginatedResponse[Player]:
    total = session.exec(select(func.count()).select_from(Player)).one()
    selection = select(Player).offset((page - 1) * page_size).limit(page_size)
    items = session.exec(selection).all()

    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, current_url=request.url)


@player_router.post(
    "", status_code=status.HTTP_201_CREATED, responses=AUTH_RESPONSES, dependencies=[Depends(verify_bearer)]
)
async def create_player(session: SessionDep, new_player: NewPlayer) -> Player:
    """Used internally and for force linking players manually."""
    # TODO: considering HTTPException as success really smells here
    try:
        await get_player_by_discord_id(session, new_player.discord_id)
        if new_player.ckey:
            await get_player_by_ckey(session, new_player.ckey)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Player already exists")
    except HTTPException as e:
        if e.status_code != status.HTTP_404_NOT_FOUND:
            raise e

    player = Player(**new_player.model_dump())
    session.add(player)
    session.commit()
    session.refresh(player)
    logger.info("Force linked %s to %s", player.ckey, player.discord_id)
    await update_player_event(player)
    return player


@player_router.get(
    "/{id}",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"description": "Player"},
        status.HTTP_404_NOT_FOUND: {"description": "Player not found"},
    },
)
async def get_player_by_id(session: SessionDep, id: int) -> Player:  # pylint: disable=redefined-builtin
    result = session.exec(select(Player).where(Player.id == id)).first()

    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")

    return result


@player_router.patch(
    "/{id}", status_code=status.HTTP_200_OK, responses=AUTH_RESPONSES, dependencies=[Depends(verify_bearer)]
)
async def update_player(session: SessionDep, id: int, player_patch: PlayerPatch) -> Player:  # pylint: disable=redefined-builtin
    player = await get_player_by_id(session, id)
    update_data = player_patch.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(player, key, value)

    session.commit()
    session.refresh(player)
    logger.info("Player updated: %s", player.model_dump_json())
    await update_player_event(player)
    return player


# endregion

# region Events


async def update_player_event(player: Player) -> None:
    await redis.send_message("link", player.model_dump_json())


# endregion
