# pyright: reportUnknownMemberType=false
from typing import Any

import aiohttp
import pytest
from app.oauth.discord.client import DiscordOAuthClient
from app.oauth.discord.exeptions import RateLimitedError, ScopeMissingError, UnauthorizedError
from app.oauth.discord.models.guild import GuildPreview
from app.oauth.discord.models.user import User
from fastapi import status
from fastapi.security import HTTPAuthorizationCredentials
from pytest_mock import MockerFixture


@pytest.fixture
def client() -> DiscordOAuthClient:
    return DiscordOAuthClient(
        client_id=123456789,
        client_secret="test_secret",
        redirect_uri="http://localhost:8000/callback",
        scopes=("identify", "guilds"),
    )


class TestDiscordOAuthClient:
    def test_init(self, client: DiscordOAuthClient) -> None:
        """Test client initialization with correct parameters."""
        assert client.client_id == 123456789
        assert client.client_secret == "test_secret"
        assert client.redirect_uri == "http://localhost:8000/callback"
        assert client.scopes == ("identify", "guilds")

    def test_get_oauth_login_url(self, client: DiscordOAuthClient) -> None:
        """Test get_oauth_login_url method with state parameter."""
        url = client.get_oauth_login_url("test_state")

        assert url.hostname == "discord.com"
        assert url.path == "/api/oauth2/authorize"
        assert "client_id=123456789" in url.query
        assert "redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fcallback" in url.query
        assert "scope=identify+guilds" in url.query
        assert "response_type=code" in url.query
        assert "state=test_state" in url.query

    async def test_request_success(self, client: DiscordOAuthClient, mocker: MockerFixture) -> None:
        """Test successful API request."""
        response_data = {"id": "123", "username": "test_user"}

        mock_response = mocker.MagicMock()
        mock_response.status = status.HTTP_200_OK
        mock_response.json = mocker.AsyncMock(return_value=response_data)

        mock_get = mocker.AsyncMock(return_value=mock_response)

        mock_session = mocker.MagicMock()
        mock_session.get = mock_get

        cm_mock = mocker.AsyncMock()
        cm_mock.__aenter__.return_value = mock_session
        mocker.patch("aiohttp.ClientSession", return_value=cm_mock)

        result: Any = await client.request("/users/@me", "test_token")

        mock_get.assert_called_once_with(
            "https://discord.com/api/v10/users/@me", headers={"Authorization": "Bearer test_token"}
        )
        assert result == response_data

    async def test_request_unauthorized(self, client: DiscordOAuthClient, mocker: MockerFixture) -> None:
        """Test unauthorized API request."""
        mock_response = mocker.MagicMock()
        mock_response.status = status.HTTP_401_UNAUTHORIZED
        mock_response.json = mocker.AsyncMock(return_value={"message": "Unauthorized"})

        mock_get = mocker.AsyncMock(return_value=mock_response)

        mock_session = mocker.MagicMock()
        mock_session.get = mock_get

        mock_cm = mocker.AsyncMock(spec=aiohttp.ClientSession)
        mock_cm.__aenter__.return_value = mock_session
        mocker.patch("aiohttp.ClientSession", return_value=mock_cm)

        with pytest.raises(UnauthorizedError):
            await client.request("/users/@me", "test_token")

    async def test_request_rate_limited(self, client: DiscordOAuthClient, mocker: MockerFixture) -> None:
        """Test rate limited API request."""
        rate_limit_data = {"message": "You are being rate limited.", "retry_after": 5}
        rate_limit_headers = {
            "X-RateLimit-Limit": "10",
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "1619283600",
        }

        mock_response = mocker.AsyncMock()
        mock_response.status = status.HTTP_429_TOO_MANY_REQUESTS
        mock_response.json.return_value = rate_limit_data
        mock_response.headers = rate_limit_headers

        mock_session = mocker.AsyncMock()
        mock_session.get.return_value = mock_response
        mock_session.__aenter__.return_value = mock_session

        mocker.patch("aiohttp.ClientSession", return_value=mock_session)

        with pytest.raises(RateLimitedError) as exc_info:
            await client.request("/users/@me", "test_token")

        mock_session.get.assert_called_once_with(
            "https://discord.com/api/v10/users/@me", headers={"Authorization": "Bearer test_token"}
        )

        assert exc_info.value.json == rate_limit_data
        assert exc_info.value.headers == rate_limit_headers
        assert exc_info.value.message == "You are being rate limited."
        assert exc_info.value.retry_after == 5

    async def test_request_post_method(self, client: DiscordOAuthClient, mocker: MockerFixture) -> None:
        """Test POST method in request."""
        expected_data = {"success": True}

        mock_response = mocker.AsyncMock()
        mock_response.status = status.HTTP_200_OK
        mock_response.json.return_value = expected_data

        mock_session = mocker.AsyncMock()
        mock_session.post.return_value = mock_response
        mock_session.__aenter__.return_value = mock_session

        mocker.patch("aiohttp.ClientSession", return_value=mock_session)

        result: Any = await client.request("/test", "test_token", method="POST")

        mock_session.post.assert_called_once_with(
            "https://discord.com/api/v10/test", headers={"Authorization": "Bearer test_token"}
        )

        assert result == expected_data

    async def test_request_invalid_method(self, client: DiscordOAuthClient) -> None:
        """Test invalid method in request."""
        for method in ["PUT", "DELETE", "OPTIONS", "PATCH", "TRACE"]:
            with pytest.raises(ValueError, match=f"Method {method} not supported"):
                await client.request("/test", "test_token", method=method)

    async def test_get_access_token(self, client: DiscordOAuthClient, mocker: MockerFixture) -> None:
        """Test getting access token with authorization code."""
        expected_access_token = "test_access_token"
        expected_refresh_token = "test_refresh_token"
        response_data = {
            "access_token": expected_access_token,
            "refresh_token": expected_refresh_token,
            "token_type": "Bearer",
            "expires_in": 604800,
        }

        mock_response = mocker.MagicMock()
        mock_response.json = mocker.AsyncMock(return_value=response_data)
        mock_post = mocker.AsyncMock(return_value=mock_response)
        mock_session = mocker.MagicMock()
        mock_session.post = mock_post

        cm_mock = mocker.AsyncMock()
        cm_mock.__aenter__.return_value = mock_session
        mocker.patch("aiohttp.ClientSession", return_value=cm_mock)

        access_token, refresh_token = await client.get_access_token("test_code")

        assert access_token == expected_access_token
        assert refresh_token == expected_refresh_token
        mock_post.assert_called_once_with(
            "https://discord.com/api/oauth2/token",
            data={
                "client_id": client.client_id,
                "client_secret": client.client_secret,
                "grant_type": "authorization_code",
                "code": "test_code",
                "redirect_uri": client.redirect_uri,
                "scope": client.scopes,
            },
        )

    async def test_refresh_access_token(self, client: DiscordOAuthClient, mocker: MockerFixture) -> None:
        """Test refreshing access token."""
        expected_access_token = "new_access_token"
        expected_refresh_token = "new_refresh_token"
        response_data = {
            "access_token": expected_access_token,
            "refresh_token": expected_refresh_token,
            "token_type": "Bearer",
            "expires_in": 604800,
        }

        mock_response = mocker.MagicMock()
        mock_response.json = mocker.AsyncMock(return_value=response_data)
        mock_post = mocker.AsyncMock(return_value=mock_response)
        mock_session = mocker.MagicMock()
        mock_session.post = mock_post

        cm_mock = mocker.AsyncMock()
        cm_mock.__aenter__.return_value = mock_session
        mocker.patch("aiohttp.ClientSession", return_value=cm_mock)

        access_token, refresh_token = await client.refresh_access_token("old_refresh_token")

        assert access_token == expected_access_token
        assert refresh_token == expected_refresh_token

        expected_payload = {
            "client_id": client.client_id,
            "client_secret": client.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": "old_refresh_token",
        }
        mock_post.assert_called_once_with("https://discord.com/api/oauth2/token", data=expected_payload)

    async def test_user(self, client: DiscordOAuthClient, mocker: MockerFixture) -> None:
        """Test getting user information."""
        mock_request = mocker.AsyncMock(return_value={"id": "123456", "username": "test_user"})
        mocker.patch.object(client, "request", mock_request)

        user = await client.user("test_token")

        mock_request.assert_called_once_with("/users/@me", "test_token")
        assert isinstance(user, User)
        assert user.id == "123456"
        assert user.username == "test_user"

    async def test_user_missing_scope(self) -> None:
        """Test getting user information with missing scope."""
        # Create client with missing identify scope
        client_without_identify = DiscordOAuthClient(
            client_id=123456789,
            client_secret="test_secret",
            redirect_uri="http://localhost:8000/callback",
            scopes=("guilds",),
        )

        with pytest.raises(ScopeMissingError) as exc_info:
            await client_without_identify.user("test_token")

        assert exc_info.value.scope == "identify"

    async def test_get_user(self, client: DiscordOAuthClient, mocker: MockerFixture) -> None:
        """Test get_user method."""
        mock_request = mocker.AsyncMock(return_value={"id": "123456", "username": "test_user"})
        mocker.patch.object(client, "request", mock_request)

        user = await client.get_user("test_token")

        mock_request.assert_called_once_with("/users/@me", "test_token")
        assert isinstance(user, User)
        assert user.id == "123456"
        assert user.username == "test_user"

    async def test_guilds(self, client: DiscordOAuthClient, mocker: MockerFixture) -> None:
        """Test getting user guilds."""
        mock_request = mocker.AsyncMock(
            return_value=[
                {
                    "id": "123",
                    "name": "Test Guild 1",
                    "icon": "abc123",
                    "owner": False,
                    "permissions": 104324161,
                    "features": ["COMMUNITY", "NEWS"],
                    "banner": "def456",
                },
                {
                    "id": "456",
                    "name": "Test Guild 2",
                    "icon": "def456",
                    "owner": True,
                    "permissions": 104324161,
                    "features": [],
                    "banner": "xyz789",
                },
            ]
        )
        mocker.patch.object(client, "request", mock_request)

        guilds = await client.guilds("test_token")

        mock_request.assert_called_once_with("/users/@me/guilds", "test_token")
        assert len(guilds) == 2
        assert all(isinstance(guild, GuildPreview) for guild in guilds)
        assert guilds[0].id == "123"
        assert guilds[0].name == "Test Guild 1"
        assert guilds[1].id == "456"
        assert guilds[1].name == "Test Guild 2"

    async def test_guilds_missing_scope(self) -> None:
        """Test getting guilds with missing scope."""
        # Create client with missing guilds scope
        client_without_guilds = DiscordOAuthClient(
            client_id=123456789,
            client_secret="test_secret",
            redirect_uri="http://localhost:8000/callback",
            scopes=("identify",),
        )

        with pytest.raises(ScopeMissingError) as exc_info:
            await client_without_guilds.guilds("test_token")

        assert exc_info.value.scope == "guilds"

    async def test_guilds_invalid_response(self, client: DiscordOAuthClient, mocker: MockerFixture) -> None:
        """Test handling invalid response from guilds endpoint."""
        mock_request = mocker.AsyncMock(return_value={"error": "Invalid response"})

        mocker.patch.object(client, "request", mock_request)

        with pytest.raises(ValueError, match="Invalid response from Discord API"):
            await client.guilds("test_token")

        mock_request.assert_called_once_with("/users/@me/guilds", "test_token")

    def test_get_token(self, client: DiscordOAuthClient, mocker: MockerFixture) -> None:
        """Test extracting token from authorization header."""
        mock_request = mocker.MagicMock()
        mock_request.headers = {"Authorization": "Bearer test_token"}

        token = client.get_token(mock_request)
        assert token == "test_token"

        # Test invalid authorization header format
        mock_request.headers = {"Authorization": "Basic test_token"}
        with pytest.raises(UnauthorizedError):
            client.get_token(mock_request)

        # Test missing authorization header
        mock_request.headers = {}
        with pytest.raises(UnauthorizedError):
            client.get_token(mock_request)

    async def test_is_authenticated(self, client: DiscordOAuthClient, mocker: MockerFixture) -> None:
        """Test authentication check."""
        # Test for successful response
        mock_request_success = mocker.AsyncMock(return_value={"application": {"id": "123456"}})

        mocker.patch.object(client, "request", mock_request_success)

        is_auth = await client.is_authenticated("valid")
        assert is_auth is True
        mock_request_success.assert_called_once_with("/oauth2/@me", "valid")

        # Test for failed response
        mock_request_failure = mocker.AsyncMock(side_effect=UnauthorizedError)

        mocker.patch.object(client, "request", mock_request_failure)

        is_auth = await client.is_authenticated("invalid")
        assert is_auth is False
        mock_request_failure.assert_called_once_with("/oauth2/@me", "invalid")

    async def test_requires_authorization(self, client: DiscordOAuthClient, mocker: MockerFixture) -> None:
        """Test authorization requirement."""
        # Test with is_authenticated returning True
        mock_auth_success = mocker.AsyncMock(return_value=True)

        mocker.patch.object(client, "is_authenticated", mock_auth_success)

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid")
        await client.requires_authorization(credentials)
        mock_auth_success.assert_called_once_with("valid")

        # Test with is_authenticated returning False
        mock_auth_failure = mocker.AsyncMock(return_value=False)

        mocker.patch.object(client, "is_authenticated", mock_auth_failure)

        with pytest.raises(UnauthorizedError):
            await client.requires_authorization(credentials)
        mock_auth_failure.assert_called_once_with("valid")
