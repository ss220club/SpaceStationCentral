import datetime

from app.database.models import Whitelist
from app.schemas.whitelist import NewWhitelistBanDiscord, NewWhitelistBanCkey

def test_create_whitelistban_by_discord(client, player_factory, wl_type, duration_days, bearer):
    player = player_factory()
    admin = player_factory()
    wl = NewWhitelistBanDiscord(
        player_discord_id=player.discord_id,
        admin_discord_id=admin.discord_id,
        duration_days=duration_days,
        reason="test"
    )
    response = client.post(f"whitelistban/{wl_type}/discord",
                           json=wl.model_dump(),
                           headers={"Authorization": f"Bearer {bearer}"})
    assert response.status_code == 201

    wl = Whitelist.model_validate(response.json())

    assert wl.player_id == player.id
    assert wl.admin_id == admin.id
    assert wl.wl_type == wl_type
    assert wl.expiration_time > datetime.datetime.now()
    assert wl.valid
