import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from app.core.config import CONFIG
from app.database.models import CkeyLinkToken, Player
from app.deps import SessionDep, verify_bearer, BEARER_DEP_RESPONSES
from app.fur_discord import DiscordOAuthClient

logger = logging.getLogger("main-logger")


router = APIRouter(prefix="/player", tags=["Player"])

CALLBACK_PATH = "/discord_oa"
oauth_client = DiscordOAuthClient(
    CONFIG.oauth.client_id, CONFIG.oauth.client_secret, f"{
        CONFIG.general.endpoint_url}{router.prefix}{CALLBACK_PATH}"
)


async def get_token_by_ckey(session: Session, ckey: str) -> str:
    """
    If token already exists, makes sure that its valid, if not - regenerates it. If token doesnt exist - generates it.
    """
    token_entry = session.exec(select(CkeyLinkToken).where(
        CkeyLinkToken.ckey == ckey)).first()
    if token_entry is None:
        token_entry = CkeyLinkToken(ckey=ckey)
    elif token_entry.expiration_time < datetime.datetime.now():
        session.delete(token_entry)
        session.commit()
        token_entry = CkeyLinkToken(ckey=ckey)
    else:
        return token_entry.token

    session.add(token_entry)
    session.commit()
    session.refresh(token_entry)

    return token_entry.token


async def get_token_owner(session: Session, token: str) -> str:
    """
    Assumes that the token is valid
    """
    return session.exec(select(CkeyLinkToken).where(CkeyLinkToken.token == token)).first().ckey


async def is_token_valid(session: Session, token: str):
    """
    Checks if the given state token is valid for the given ckey.
    """
    token_entry = session.exec(select(CkeyLinkToken).where(
        CkeyLinkToken.token == token).where(CkeyLinkToken.expiration_time > datetime.datetime.now())).first()
    return token_entry is not None


@router.get("/login", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
async def login(token: str) -> RedirectResponse:
    """
    Redirects to the discord oauth2 login page with the given ckey and state token
    """
    return RedirectResponse(oauth_client.get_oauth_login_url(token))


@router.post("/token", status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_bearer)], responses=BEARER_DEP_RESPONSES)
async def generate_state(session: SessionDep, ckey: str) -> str:
    """
    Generates a state token for the given ckey and returns it. The state token
    is used to validate the authorization flow.
    """
    return await get_token_by_ckey(session, ckey)


@router.get(CALLBACK_PATH)
async def callback(session: SessionDep, code: str, state: str) -> Player:
    """
    The callback endpoint for the discord oauth2 flow. It takes the code and state parameters
    and verifies the state token. If the state token is invalid, it raises a 401 Unauthorized
    response. If the state token is valid, it uses the code to get an access token for the
    discord user. It then checks if the player is already linked with the discord user. If
    the player is already linked, it raises a 409 Conflict response. If the player is not
    already linked, it creates a new Player object with the ckey and discord_id and adds it
    to the database. It then returns the newly created Player object.
    """
    discord_token, _ = await oauth_client.get_access_token(code)
    token = state
    if not await is_token_valid(session, token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong or expired token")
    ckey = await get_token_owner(session, token)
    if ckey is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong or expired token")
    discord_user = await oauth_client.get_user(discord_token)
    discord_id = discord_user.id

    if session.exec(select(Player).where(Player.ckey == ckey or Player.discord_id == discord_id)).first() is not None:
        logger.debug(
            "Player already linked and tried to link: %s %s", ckey, discord_id)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Player already linked")

    link = Player(ckey=ckey, discord_id=discord_id)
    session.add(link)
    session.commit()
    session.refresh(link)

    logger.info("Linked %s to %s", link.ckey, link.discord_id)

    return link


# TODO: Add paginationm just in case.
@router.get(
    "/players",
    responses={
        200: {"description": "List of matching players"},
        400: {"description": "Invalid filter combination"},
        404: {"description": "No players found"}
    }
)
async def get_players(session: SessionDep,
                     ckey: str = None,
                     discord_id: str = None,
                     limit: int = 10) -> list[Player]:
    """
    Get players by ckey or discord_id, but not both.
    """
    selection = select(Player)
    match ckey, discord_id:
        case None, None:
            pass
        case None, discord_id:
            selection = selection.where(Player.discord_id == discord_id)
        case ckey, None:
            selection = selection.where(Player.ckey == ckey)
        case ckey, discord_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid filter combination"
            )

    players = session.exec(selection).limit(limit).all()
    if len(players) == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No players found")
    return players
