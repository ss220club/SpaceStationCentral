import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException, status
from sqlmodel import Session, select
import datetime

from app.routes.player import (
    get_token_by_ckey, 
    get_token_owner, 
    is_token_valid, 
    login, 
    generate_state, 
    callback, 
    get_player_by_ckey, 
    get_player_by_discord
)
from app.database.models import OneTimeToken, Player

@pytest.mark.asyncio
@pytest.mark.parametrize("test_input,expected", [
    ("test_ckey", "valid_token"),
    ("existing_ckey", "existing_token"),
])
async def test_get_token_by_ckey(test_input, expected, mocker):
    # Arrange
    mock_session = AsyncMock(spec=Session)
    mock_select = mocker.patch('app.routes.player.select')
    mock_session.exec.return_value.first.return_value = None

    # Act
    result = await get_token_by_ckey(mock_session, test_input)

    # Assert
    assert result is not None
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()

@pytest.mark.asyncio
@pytest.mark.parametrize("test_input,expected", [
    ("valid_token", "test_ckey"),
])
async def test_get_token_owner(test_input, expected, mocker):
    # Arrange
    mock_session = AsyncMock(spec=Session)
    mock_token_entry = mocker.Mock()
    mock_token_entry.ckey = expected
    mock_session.exec.return_value.first.return_value = mock_token_entry

    # Act
    result = await get_token_owner(mock_session, test_input)

    # Assert
    assert result == expected

@pytest.mark.asyncio
@pytest.mark.parametrize("token,is_valid", [
    ("valid_token", True),
    ("expired_token", False),
])
async def test_is_token_valid(token, is_valid, mocker):
    # Arrange
    mock_session = AsyncMock(spec=Session)
    if is_valid:
        mock_token_entry = mocker.Mock()
        mock_token_entry.expiry = datetime.datetime.now() + datetime.timedelta(hours=1)
        mock_session.exec.return_value.first.return_value = mock_token_entry
    else:
        mock_session.exec.return_value.first.return_value = None

    # Act
    result = await is_token_valid(mock_session, token)

    # Assert
    assert result == is_valid

@pytest.mark.asyncio
@pytest.mark.parametrize("token,expected_url", [
    ("test_token", "https://discord.com/oauth_url"),
])
async def test_login(token, expected_url, mocker):
    # Arrange
    mock_oauth_client = mocker.patch('app.routes.player.oauth_client')
    mock_oauth_client.get_oauth_login_url.return_value = expected_url

    # Act
    response = await login(token)

    # Assert
    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert response.headers['location'] == expected_url

@pytest.mark.asyncio
@pytest.mark.parametrize("ckey,expected_token", [
    ("test_ckey", "generated_token"),
])
async def test_generate_state(ckey, expected_token, mocker):
    # Arrange
    mock_session = AsyncMock(spec=Session)
    mock_session.exec.return_value.first.return_value = None

    # Act
    result = await generate_state(mock_session, ckey)

    # Assert
    assert result is not None

@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", [
    {
        "code": "valid_code",
        "state": "valid_state",
        "discord_user_id": "123456",
        "existing_player": None,
        "expected_status": status.HTTP_200_OK
    },
    {
        "code": "valid_code",
        "state": "invalid_state",
        "discord_user_id": "123456",
        "existing_player": None,
        "expected_status": status.HTTP_401_UNAUTHORIZED
    },
])
async def test_callback(scenario, mocker):
    # Arrange
    mock_session = AsyncMock(spec=Session)
    mock_oauth_client = mocker.patch('app.routes.player.oauth_client')
    
    # Use AsyncMock for async methods
    mock_oauth_client.get_access_token = AsyncMock(return_value=("discord_token", None))
    mock_oauth_client.get_user = AsyncMock(return_value=mocker.Mock(id=scenario['discord_user_id']))
    
    mocker.patch('app.routes.player.is_token_valid', return_value=scenario['state'] == 'valid_state')
    mocker.patch('app.routes.player.get_token_owner', return_value='test_ckey')
    
    mock_session.exec.return_value.first.return_value = scenario['existing_player']

    # Act & Assert
    if scenario['expected_status'] == status.HTTP_401_UNAUTHORIZED:
        with pytest.raises(HTTPException) as exc_info:
            await callback(mock_session, scenario['code'], scenario['state'])
        assert exc_info.value.status_code == scenario['expected_status']
    else:
        result = await callback(mock_session, scenario['code'], scenario['state'])
        assert result is not None

@pytest.mark.asyncio
@pytest.mark.parametrize("ckey,expected_status", [
    ("existing_ckey", status.HTTP_200_OK),
    ("non_existing_ckey", status.HTTP_404_NOT_FOUND),
])
async def test_get_player_by_ckey(ckey, expected_status, mocker):
    # Arrange
    mock_session = AsyncMock(spec=Session)
    if expected_status == status.HTTP_200_OK:
        mock_player = Player(ckey=ckey, discord_id="123")
        mock_session.exec.return_value.first.return_value = mock_player
    else:
        mock_session.exec.return_value.first.return_value = None

    # Act & Assert
    if expected_status == status.HTTP_404_NOT_FOUND:
        with pytest.raises(HTTPException) as exc_info:
            await get_player_by_ckey(mock_session, ckey)
        assert exc_info.value.status_code == expected_status
    else:
        result = await get_player_by_ckey(mock_session, ckey)
        assert result.ckey == ckey

@pytest.mark.asyncio
@pytest.mark.parametrize("discord_id,expected_status", [
    ("123456", status.HTTP_200_OK),
    ("non_existing_id", status.HTTP_404_NOT_FOUND),
])
async def test_get_player_by_discord(discord_id, expected_status, mocker):
    # Arrange
    mock_session = AsyncMock(spec=Session)
    if expected_status == status.HTTP_200_OK:
        mock_player = Player(ckey="test_ckey", discord_id=discord_id)
        mock_session.exec.return_value.first.return_value = mock_player
    else:
        mock_session.exec.return_value.first.return_value = None

    # Act & Assert
    if expected_status == status.HTTP_404_NOT_FOUND:
        with pytest.raises(HTTPException) as exc_info:
            await get_player_by_discord(mock_session, discord_id)
        assert exc_info.value.status_code == expected_status
    else:
        result = await get_player_by_discord(mock_session, discord_id)
        assert result.discord_id == discord_id
