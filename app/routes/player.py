import datetime
import logging
logger = logging.getLogger("main-logger")

from fastapi import APIRouter, HTTPException
from fastapi import status
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select
from app.fur_discord import DiscordOAuthClient

from app.core.config import Config
from app.database.models import OneTimeToken, Player
from app.deps import SessionDep, BearerDep

router = APIRouter(prefix="/player", tags=["Player"])

CALLBACK_PATH = "/discord_oa"
oauth_client = DiscordOAuthClient(
    Config.Oauth.CLIENT_ID, Config.Oauth.CLEINT_SECRET, f"{Config.General.ENDPOINT_URL}{router.prefix}{CALLBACK_PATH}"
)

def get_token_by_ckey(session: Session, ckey: str) -> str:
    token_entry = session.exec(select(OneTimeToken).where(OneTimeToken.ckey == ckey)).first()
    if token_entry is None:
        token_entry = OneTimeToken(ckey=ckey)
    elif token_entry.expiry < datetime.datetime.now():
        session.delete(token_entry)
        session.commit()
        token_entry = OneTimeToken(ckey=ckey)
    else:
        return token_entry.token

    session.add(token_entry)
    session.commit()
    session.refresh(token_entry)

    return token_entry.token

def get_token_owner(session: Session, token: str) -> str:
    """
    Assumes that the token is valid
    """
    return session.exec(select(OneTimeToken).where(OneTimeToken.token == token)).first().ckey

def is_state_valid(session: Session, token: str):
    """
    Checks if the given state token is valid for the given ckey.
    """
    token_entry = session.exec(select(OneTimeToken).where(OneTimeToken.token == token and OneTimeToken.expiry > datetime.datetime.now())).first()
    if token_entry is None:
        return False
    return True

@router.get("/login", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
async def login(token: str) -> RedirectResponse:
    """
    Redirects to the discord oauth2 login page with the given ckey and state token
    """
    return RedirectResponse(oauth_client.get_oauth_login_url(token))

@router.get("/token/{ckey}")
async def generate_state(session: SessionDep, bearer: BearerDep, ckey: str):
    """
    Generates a state token for the given ckey and returns it. The state token
    is used to validate the authorization flow.
    """
    logger.info("%s", bearer)
    token = get_token_by_ckey(session, ckey)
    return token

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
    if not is_state_valid(session, token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong or expired token")
    ckey = get_token_owner(session, token)
    user = await oauth_client.get_user(discord_token)
    discord_id = user.id

    if session.exec(select(Player).where(Player.ckey == ckey or Player.discord_id == discord_id)).first() is not None:
        logger.debug("Player already linked and tried to link: %s %s", ckey, discord_id)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Player already linked")

    link = Player(ckey=ckey, discord_id=discord_id)
    session.add(link)
    session.commit()
    session.refresh(link)

    logger.info("Linked %s to %s", link.ckey, link.discord_id)

    return link


@router.get("/ckey/{ckey}")
async def get_player_by_ckey(session: SessionDep, ckey: str):
    """
    Retrieves a player by their ckey.
    """

    player = session.exec(select(Player).where(Player.ckey == ckey)).first()
    if player is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")
    return player

@router.get("/discord/{discord_id}")
async def get_player_by_discord(session: SessionDep, discord_id: str):
    """
    Retrieves a player by their discord ID.
    """
    player = session.exec(select(Player).where(Player.discord_id == discord_id)).first()
    if player is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")
    return player

