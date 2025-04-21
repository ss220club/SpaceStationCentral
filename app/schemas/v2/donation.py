from app.database.models import DonationBase, Player


# region Get
class DonationNested(DonationBase):
    player: Player


# endregion
