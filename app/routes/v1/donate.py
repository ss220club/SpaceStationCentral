import datetime
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import select
from sqlmodel.sql.expression import SelectOfScalar
from app.database.models import Donation, Player
from app.schemas.donate import NewDonationDiscord
from app.deps import SessionDep, verify_bearer

from app.schemas.generic import PaginatedResponse, paginate_selection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/donate", tags=["Donate"])


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


@router.get("s", status_code=status.HTTP_200_OK)
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


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_donation(session: SessionDep, donation: Donation) -> Donation:
    session.add(donation)
    session.commit()
    session.refresh(donation)

    logger.info("Donation created: %s", donation.model_dump_json())

    return donation

WHITELIST_POST_RESPONSES = {
    status.HTTP_201_CREATED: {"description": "Whitelist created"},
    status.HTTP_404_NOT_FOUND: {"description": "Player not found"},
}


@router.post("/by-discord", status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_bearer)], responses=WHITELIST_POST_RESPONSES)
async def create_donation_by_discord(session: SessionDep, new_donation: NewDonationDiscord) -> Donation:
    player = session.exec(
        select(Player).where(Player.discord_id == new_donation.discord_id)
    ).first()

    if player is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")

    donation = Donation(
        player_id=player.id,
        tier=new_donation.tier
    )

    return await create_donation(session, donation)
