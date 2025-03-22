# pyright: reportUnknownMemberType = false
import re
from typing import Any

import aiohttp
from aiocache import cached  # pyright: ignore[reportMissingTypeStubs]
from fastapi import Depends, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.datastructures import URL

from app.core.typing import JSONAny
from app.fur_discord.config import DISCORD_API_URL, DISCORD_OAUTH_AUTHENTICATION_URL, DISCORD_TOKEN_URL
from app.fur_discord.exeptions import RateLimitedError, ScopeMissingError, UnauthorizedError
from app.fur_discord.models import GuildPreview, User


class DiscordOAuthClient:
    """Client for Discord Oauth2."""

    def __init__(
        self, client_id: int, client_secret: str, redirect_uri: str, scopes: tuple[str, ...] = ("identify",)
    ) -> None:
        """
        Initialize the Discord OAuth client.

        Args:
            client_id: Discord application client ID.
            client_secret: Discord application client secret.
            redirect_uri: Discord application redirect URI.
            scopes: Discord application scopes.
        """
        self.client_id: int = client_id
        self.client_secret: str = client_secret
        self.redirect_uri: str = redirect_uri
        self.scopes: str = " ".join(scopes)

    @property
    def oauth_login_url(self) -> str:
        """Return a Discord Login URL."""
        client_id = f"client_id={self.client_id}"
        redirect_uri = f"redirect_uri={self.redirect_uri}"
        scopes = f"scope={self.scopes}"
        response_type = "response_type=code"
        return f"{DISCORD_OAUTH_AUTHENTICATION_URL}?{client_id}&{redirect_uri}&{scopes}&{response_type}"

    def get_oauth_login_url(self, state: str | None) -> str:
        """Return a Discord Login URL with state."""
        url = URL(DISCORD_OAUTH_AUTHENTICATION_URL).include_query_params(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            scope=self.scopes,
            response_type="code",
            state=state or "",
        )
        return str(url)

    @cached(ttl=550)
    async def request(self, route: str, token: str | None = None, method: str = "GET") -> JSONAny:
        headers = {"Authorization": f"Bearer {token or ''}"}
        if method == "GET":
            async with aiohttp.ClientSession() as session:
                resp = await session.get(f"{DISCORD_API_URL}{route}", headers=headers)
                data = await resp.json()
        elif method == "POST":
            async with aiohttp.ClientSession() as session:
                resp = await session.post(f"{DISCORD_API_URL}{route}", headers=headers)
                data = await resp.json()
        else:
            raise ValueError(f"Method {method} not supported")
        if resp.status == status.HTTP_401_UNAUTHORIZED:
            raise UnauthorizedError
        if resp.status == status.HTTP_429_TOO_MANY_REQUESTS:
            raise RateLimitedError(data, dict(resp.headers))
        return data

    async def get_access_token(self, code: str) -> tuple[str | None, str | None]:
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "scope": self.scopes,
        }
        async with aiohttp.ClientSession() as session, session.post(DISCORD_TOKEN_URL, data=payload) as resp:
            resp_json: dict[str, Any] = await resp.json()
            return resp_json.get("access_token"), resp_json.get("refresh_token")

    async def refresh_access_token(self, refresh_token: str) -> tuple[str | None, str | None]:
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        async with aiohttp.ClientSession() as session, session.post(DISCORD_TOKEN_URL, data=payload) as resp:
            resp_json: dict[str, Any] = await resp.json()
            return resp_json.get("access_token"), resp_json.get("refresh_token")

    async def user(self, token: str) -> User:
        if "identify" not in self.scopes:
            raise ScopeMissingError("identify")
        route = "/users/@me"
        return User.model_validate(await self.request(route, token))

    async def get_user(self, token: str) -> User:
        route = "/users/@me"
        response: Any = await self.request(route, token)
        return User.model_validate(response)

    async def guilds(self, token: str) -> list[GuildPreview]:
        if "guilds" not in self.scopes:
            raise ScopeMissingError("guilds")

        route = "/users/@me/guilds"
        response: Any = await self.request(route, token)
        if not isinstance(response, list):
            raise ValueError("Invalid response from Discord API")

        guilds: list[dict[str, Any]] = response
        return [GuildPreview.model_validate(guild) for guild in guilds]

    def get_token(self, request: Request) -> str:
        authorization_header = request.headers.get("Authorization")
        if not authorization_header:
            raise UnauthorizedError

        if match := re.compile(r"^Bearer (?P<token>\S+)$").match(authorization_header):
            return match["token"]
        raise UnauthorizedError

    async def is_auntheficated(self, token: str) -> bool:
        route = "/oauth2/@me"
        try:
            await self.request(route, token)
            return True
        except UnauthorizedError:
            return False

    async def requires_authorization(self, bearer: HTTPAuthorizationCredentials | None = None) -> None:
        credentials = bearer or Depends(HTTPBearer())
        if not await self.is_auntheficated(credentials.credentials):
            raise UnauthorizedError
