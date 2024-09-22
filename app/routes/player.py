import logging
logger = logging.getLogger("main-logger")

from hashlib import md5
from fastapi import APIRouter, Depends, HTTPException
from fastapi import status
from fastapi.responses import RedirectResponse
from sqlmodel import select
from app.fur_discord import DiscordOAuthClient, Unauthorized, User

from app.core.config import Config
from app.database.models import CkeyToDiscord
from app.deps import SessionDep

router = APIRouter(prefix="/player", tags=["Player"])

CALLBACK_PATH = "/discord_oa"
oauth_client = DiscordOAuthClient(
    Config.Oauth.CLIENT_ID, Config.Oauth.CLEINT_SECRET, f"{Config.General.ENDPOINT_URL}{router.prefix}{CALLBACK_PATH}"
)

@router.get("/login")
async def login(ckey: str, token: str):
    return RedirectResponse(oauth_client.get_oauth_login_url(f"{ckey}+{token}"))

def generate_token(ckey: str):
    token = md5((ckey + Config.Oauth.STATE_SECRET).encode()).hexdigest()
    return token

def is_state_valid(ckey: str, token: str):
    return generate_token(ckey) == token

@router.get("/login/g/{ckey}")
async def generate_state(ckey: str):
    token = generate_token(ckey)
    return token

@router.get(CALLBACK_PATH)
async def callback(session: SessionDep, code: str, state: str):
    discord_token, _ = await oauth_client.get_access_token(code)
    ckey, token = state.split(" ")
    if not is_state_valid(ckey, token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Spoofed or invalid state")
    user = await oauth_client.get_user(discord_token)
    discord_id = user.id

    if session.exec(select(CkeyToDiscord).where(CkeyToDiscord.ckey == ckey or CkeyToDiscord.discord_id == discord_id)).first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Player already linked")

    link = CkeyToDiscord(ckey=ckey, discord_id=discord_id)
    session.add(link)
    session.commit()
    session.refresh(link)

    return link


@router.get("/ckey/{ckey}")
async def get_player(session: SessionDep, ckey: str):
    player = session.exec(select(CkeyToDiscord).where(CkeyToDiscord.ckey == ckey)).first()
    if player is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")
    return player

@router.get("/discord/{discord_id}")
async def get_player(session: SessionDep, discord_id: str):
    player = session.exec(select(CkeyToDiscord).where(CkeyToDiscord.discord_id == discord_id)).first()
    if player is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")
    return player

