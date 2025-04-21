import datetime

from pydantic import BaseModel


class NewDonationBase(BaseModel):
    tier: int
    duration_days: int = 30


class NewDonationDiscord(NewDonationBase):
    discord_id: str


class DonationPatch(BaseModel):
    expiration_time: datetime.datetime
