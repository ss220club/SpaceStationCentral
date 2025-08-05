from app.database.models import Player
from app.schemas.v2.player import PlayerNested
from fastapi.testclient import TestClient


def test_get_player_by_id(client: TestClient, player: Player) -> None:
    response = client.get(f"/v2/players/{player.id}")
    assert response.status_code == 200
    nested_player = PlayerNested.model_validate(response.json())
    assert player == Player.model_validate(nested_player)


def test_get_player_by_discord_id(client: TestClient, player: Player) -> None:
    response = client.get(f"/v2/players/discord/{player.discord_id}")
    assert response.status_code == 200
    nested_player = PlayerNested.model_validate(response.json())
    assert player == Player.model_validate(nested_player)


def test_get_invalid_player_by_discord_id(client: TestClient) -> None:
    response = client.get("/v2/players/discord/invalid_discord_id")
    assert response.status_code == 404


def test_get_player_by_ckey(client: TestClient, player: Player) -> None:
    response = client.get(f"/v2/players/ckey/{player.ckey}")
    assert response.status_code == 200
    nested_player = PlayerNested.model_validate(response.json())
    assert player == Player.model_validate(nested_player)
