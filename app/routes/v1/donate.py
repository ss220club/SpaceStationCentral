import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import select
from sqlmodel.sql.expression import SelectOfScalar

from app.database.models import Donation, Player
from app.deps import SessionDep, verify_bearer
from app.routes.v1.player import create_player, get_or_create_player_by_discord_id
from app.schemas.donate import NewDonationDiscord
from app.schemas.generic import PaginatedResponse, paginate_selection
from app.schemas.player import NewPlayer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/donates", tags=["Donate"])


def filter_donations(selection: SelectOfScalar[Donation],
                     ckey: str | None = None,
                     discord_id: str | None = None,
                     active_only: bool = True) -> SelectOfScalar[Donation]:
    if ckey:
        selection = selection.where(Player.ckey == ckey)
    if discord_id:
        selection = selection.where(Player.discord_id == discord_id)
    if active_only:
        selection = selection.where(Donation.valid).where(
            Donation.expiration_time > datetime.datetime.now())
    return selection


@router.get("", status_code=status.HTTP_200_OK)
async def get_donations(session: SessionDep,
                        request: Request,
                        ckey: str | None = None,
                        discord_id: str | None = None,
                        active_only: bool = True,
                        page: int = 1,
                        page_size: int = 50) -> PaginatedResponse[Donation]:
    selection = select(Donation).join(
        Player, Player.id == Donation.player_id)

    selection = filter_donations(selection, ckey, discord_id, active_only)

    return paginate_selection(session, selection, request, page, page_size)


async def create_donation_helper(session: SessionDep, donation: Donation) -> Donation:
    session.add(donation)
    session.commit()
    session.refresh(donation)

    logger.info("Donation created: %s", donation.model_dump_json())

    return donation

WHITELIST_POST_RESPONSES = {
    status.HTTP_201_CREATED: {"description": "Whitelist created"},
    status.HTTP_404_NOT_FOUND: {"description": "Player not found"},
}


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_bearer)], responses=WHITELIST_POST_RESPONSES)
async def create_donation_by_discord(session: SessionDep, new_donation: NewDonationDiscord) -> Donation:
    """
    Creating a new donation from any other identifier doesnt make much sense
    """
    player = await get_or_create_player_by_discord_id(session, new_donation.discord_id)

    donation = Donation(
        player_id=player.id,
        tier=new_donation.tier
    )

    return await create_donation_helper(session, donation)
