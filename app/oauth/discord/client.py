# pyright: reportUnknownMemberType = false
import re
from os import environ
from typing import Any

import aiohttp
from aiocache import cached  # pyright: ignore[reportMissingTypeStubs]
from app.core.config import ConfigSection
from app.core.typing import JSONAny
from app.oauth.discord.exeptions import RateLimitedError, ScopeMissingError, UnauthorizedError
from app.oauth.discord.models import GuildPreview, User
from fastapi import Depends, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.datastructures import URL


DISCORD_URL = "https://discord.com"
DISCORD_API_URL = f"{DISCORD_URL}/api/v10"
DISCORD_OAUTH_URL = f"{DISCORD_URL}/api/oauth2"
DISCORD_TOKEN_URL = f"{DISCORD_OAUTH_URL}/token"
DISCORD_OAUTH_AUTHENTICATION_URL = f"{DISCORD_OAUTH_URL}/authorize"


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
        self.scopes: tuple[str, ...] = scopes

    def get_oauth_login_url(self, state: str) -> URL:
        """Return a Discord Login URL with state."""
        return URL(DISCORD_OAUTH_AUTHENTICATION_URL).include_query_params(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            scope=" ".join(self.scopes),
            response_type="code",
            state=state,
        )

    @cached(ttl=550, skip_cache_func=lambda _: environ.get(ConfigSection.TEST_ENV) == "true")  # pyright: ignore [reportUnknownLambdaType]
    async def request(self, route: str, token: str, method: str = "GET") -> JSONAny:
        headers = {"Authorization": f"Bearer {token}"}
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
        async with aiohttp.ClientSession() as session:
            resp = await session.post(DISCORD_TOKEN_URL, data=payload)
            resp_json: dict[str, Any] = await resp.json()
            return resp_json.get("access_token"), resp_json.get("refresh_token")

    async def refresh_access_token(self, refresh_token: str) -> tuple[str | None, str | None]:
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        async with aiohttp.ClientSession() as session:
            resp = await session.post(DISCORD_TOKEN_URL, data=payload)
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

    @staticmethod
    def get_token(request: Request) -> str:
        authorization_header = request.headers.get("Authorization")
        if not authorization_header:
            raise UnauthorizedError

        if match := re.compile(r"^Bearer (?P<token>\S+)$").match(authorization_header):
            return match["token"]
        raise UnauthorizedError

    async def is_authenticated(self, token: str) -> bool:
        route = "/oauth2/@me"
        try:
            await self.request(route, token)
            return True
        except UnauthorizedError:
            return False

    async def requires_authorization(self, bearer: HTTPAuthorizationCredentials | None = None) -> None:
        credentials = bearer or Depends(HTTPBearer())
        if not await self.is_authenticated(credentials.credentials):
            raise UnauthorizedError
