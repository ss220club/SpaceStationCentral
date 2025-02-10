import datetime
from pydantic import BaseModel


class NewDonationBase(BaseModel):
    tier: int


class NewDonationDiscord(NewDonationBase):
    discord_id: str
