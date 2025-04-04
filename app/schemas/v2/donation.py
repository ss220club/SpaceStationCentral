from app.database.models import DonationBase, Player


# region Get
class DonationCascade(DonationBase):
    player: Player


# endregion
