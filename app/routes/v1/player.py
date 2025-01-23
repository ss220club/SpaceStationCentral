import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func
from sqlmodel import Session, select

from app.core.config import CONFIG
from app.database.models import CkeyLinkToken, Player
from app.deps import SessionDep, verify_bearer, BEARER_DEP_RESPONSES
from app.fur_discord import DiscordOAuthClient
from app.schemas.generic import PaginatedResponse

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
    token = session.exec(select(CkeyLinkToken).where(
        CkeyLinkToken.token == token
    ).where(CkeyLinkToken.expiration_time > datetime.datetime.now())).first()
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong or expired token")

    ckey = token.ckey
    discord_user = await oauth_client.get_user(discord_token)
    discord_id = discord_user.id

    if session.exec(select(Player).where(Player.ckey == ckey or Player.discord_id == discord_id)).first() is not None:
        logger.debug(
            "Player already linked and tried to link: %s %s", ckey, discord_id)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Player already linked")

    link = Player(ckey=ckey, discord_id=discord_id)
    session.add(link)
    session.delete(token)
    session.commit()
    session.refresh(link)

    logger.info("Linked %s to %s", link.ckey, link.discord_id)

    return link


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
)
async def get_player(session: SessionDep,
                     ckey: str | None = None,
                     discord_id: str | None = None) -> Player:
    """
    Get players by ckey or discord_id, but not both.
    """
    selection = select(Player)
    if ckey is not None:
        selection = selection.where(Player.ckey == ckey)
    if discord_id is not None:
        selection = selection.where(Player.discord_id == discord_id)

    return session.exec(selection).first()

# /players/


@router.get("s/", status_code=status.HTTP_200_OK)
async def get_players(session: SessionDep, request: Request, page: int = 1, page_size: int = 50) -> PaginatedResponse[Player]:
    total = session.exec(select(func.count()).select_from(Player)).first()
    selection = select(Player).offset((page-1)*page_size).limit(page_size)
    items = session.exec(selection).all()
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        current_url=request.url
    )
