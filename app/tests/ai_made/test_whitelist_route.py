import pytest
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlmodel import Session, select
from unittest.mock import Mock

from app.database.models import Whitelist, WhitelistBan, Player
from app.routes.whitelist import (
    create_whitelist, 
    get_whitelist_by_ckey, 
    get_whitelist_by_discord, 
    ban_whitelist, 
    get_whitelist_bans_by_discord, 
    pardon_whitelist_ban
)

@pytest.mark.asyncio
@pytest.mark.parametrize("test_input", [
    {
        "id": "valid_whitelist_creation",
        "player_id": "discord123",
        "type": "antag",
        "issue_time": datetime.now(),
        "ignore_bans": False,
        "expected_status": status.HTTP_201_CREATED
    },
    {
        "id": "whitelist_creation_with_ignore_bans",
        "player_id": "discord456",
        "type": "admin",
        "issue_time": datetime.now(),
        "ignore_bans": True,
        "expected_status": status.HTTP_201_CREATED
    }
])
async def test_create_whitelist(test_input, mocker):
    # Arrange
    session_mock = Mock(spec=Session)
    session_mock.exec.return_value.first.return_value = None
    wl = Whitelist(
        player_id=test_input["player_id"], 
        type=test_input["type"], 
        issue_time=test_input["issue_time"]
    )

    # Act
    result = await create_whitelist(
        session=session_mock, 
        wl=wl, 
        ignore_bans=test_input["ignore_bans"]
    )

    # Assert
    assert result == wl
    session_mock.add.assert_called_once_with(wl)
    session_mock.commit.assert_called_once()
    session_mock.refresh.assert_called_once_with(wl)

@pytest.mark.asyncio
@pytest.mark.parametrize("test_input", [
    {
        "id": "banned_player_without_ignore",
        "player_id": "discord789",
        "type": "antag",
        "issue_time": datetime.now(),
        "ignore_bans": False,
        "existing_ban": WhitelistBan(
            player_id="discord789", 
            type="antag", 
            valid=True, 
            issue_time=datetime.now() - timedelta(days=1), 
            duration=timedelta(days=7)
        )
    }
])

@pytest.mark.asyncio
async def test_create_whitelist_with_active_ban(test_input, mocker):
    # Arrange
    session_mock = Mock(spec=Session)
    session_mock.exec.return_value.first.return_value = test_input["existing_ban"]
    wl = Whitelist(
        player_id=test_input["player_id"], 
        type=test_input["type"], 
        issue_time=test_input["issue_time"]
    )

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await create_whitelist(
            session=session_mock, 
            wl=wl, 
            ignore_bans=test_input["ignore_bans"]
        )
    
    assert exc_info.value.status_code == status.HTTP_409_CONFLICT

@pytest.mark.asyncio
@pytest.mark.parametrize("test_input", [
    {
        "id": "get_whitelist_by_existing_ckey",
        "ckey": "player1",
        "valid": True,
        "expected_count": 2
    },
    {
        "id": "get_whitelist_by_nonexistent_ckey",
        "ckey": "nonexistent",
        "valid": True,
        "expected_count": 0
    }
])
async def test_get_whitelist_by_ckey(test_input, mocker):
    # Arrange
    session_mock = Mock(spec=Session)
    
    # AI isnt capable of joins, lol
    if test_input["ckey"] == "player1":
        mock_whitelists = [
            Whitelist(id=1, player_id="discord1", valid=True),
            Whitelist(id=2, player_id="discord2", valid=True)
        ]
    else:
        mock_whitelists = []
    
    session_mock.exec.return_value.all.return_value = mock_whitelists

    # Act
    result = await get_whitelist_by_ckey(
        session=session_mock, 
        ckey=test_input["ckey"], 
        valid=test_input["valid"]
    )

    # Assert
    assert len(result) == test_input["expected_count"]



# Additional tests for other routes would follow similar patterns
