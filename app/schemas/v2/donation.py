from app.database.models import DonationBase, Player


class DonationCascade(DonationBase):
    player: Player
