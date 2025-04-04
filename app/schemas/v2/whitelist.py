from app.database.models import Player, WhitelistBanBase, WhitelistBase


# region Get
class WhitelistNested(WhitelistBase):
    player: Player
    admin: Player


class WhitelistBanNested(WhitelistBanBase):
    player: Player
    admin: Player


# endregion
