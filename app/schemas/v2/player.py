from app.database.models import Donation, PlayerBase, Whitelist, WhitelistBan


# region Get
class PlayerCascade(PlayerBase):
    whitelists: list[Whitelist]
    whitelists_issued: list[Whitelist]

    whitelist_bans: list[WhitelistBan]
    whitelist_bans_issued: list[WhitelistBan]

    donations: list[Donation]


# endregion
