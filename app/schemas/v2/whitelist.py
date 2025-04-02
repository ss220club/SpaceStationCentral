from app.database.models import Player, WhitelistBanBase, WhitelistBase


class WhitelistCascade(WhitelistBase):
    player: Player
    admin: Player


class WhitelistBanCascade(WhitelistBanBase):
    player: Player
    admin: Player
