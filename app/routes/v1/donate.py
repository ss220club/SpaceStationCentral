import logging
from datetime import UTC, datetime, timedelta
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import select
from sqlmodel.sql.expression import Select

from app.database.models import Donation, Player
from app.deps import SessionDep, verify_bearer
from app.routes.v1.player import get_or_create_player_by_discord_id
from app.schemas.donate import DonationPatch, NewDonationDiscord
from app.schemas.generic import PaginatedResponse, paginate_selection


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/donates", tags=["Donate"])


def filter_donations(
    selection: Select[Donation],
    ckey: str | None = None,
    discord_id: str | None = None,
    active_only: bool = True,
) -> Select[Donation]:
    if ckey:
        selection = selection.where(Player.ckey == ckey)
    if discord_id:
        selection = selection.where(Player.discord_id == discord_id)
    if active_only:
        selection = selection.where(Donation.valid).where(Donation.expiration_time > datetime.now(UTC))
    return selection


@router.get("", status_code=status.HTTP_200_OK)
async def get_donations(
    session: SessionDep,
    request: Request,
    ckey: str | None = None,
    discord_id: str | None = None,
    active_only: bool = True,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedResponse[Donation]:
    selection = cast(Select[Donation], select(Donation).join(Player))
    selection = filter_donations(selection, ckey, discord_id, active_only)

    return paginate_selection(session, selection, request, page, page_size)


@router.get("/{id}", status_code=status.HTTP_200_OK)
async def get_donation_by_id(session: SessionDep, id: int) -> Donation | None:
    return session.exec(select(Donation).where(Donation.id == id)).first()


async def create_donation_helper(session: SessionDep, donation: Donation) -> Donation:
    session.add(donation)
    session.commit()
    session.refresh(donation)

    logger.info("Donation created: %s", donation.model_dump_json())

    return donation


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_bearer)],
    responses={
        status.HTTP_201_CREATED: {"description": "Whitelist created"},
        status.HTTP_404_NOT_FOUND: {"description": "Player not found"},
    },
)
async def create_donation_by_discord(session: SessionDep, new_donation: NewDonationDiscord) -> Donation:
    """Creating a new donation from any other identifier doesnt make much sense."""
    player = await get_or_create_player_by_discord_id(session, new_donation.discord_id)

    donation = Donation(
        player_id=cast(int, player.id),
        tier=new_donation.tier,
        issue_time=datetime.now(UTC),
        expiration_time=datetime.now(UTC) + timedelta(days=new_donation.duration_days),
        valid=True,
    )

    return await create_donation_helper(session, donation)


@router.patch("/{id}", status_code=status.HTTP_200_OK, dependencies=[Depends(verify_bearer)])
async def update_donation(session: SessionDep, id: int, donation_patch: DonationPatch) -> Donation:  # pylint: disable=redefined-builtin
    donation = await get_donation_by_id(session, id)
    if not donation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found")

    update_data = donation_patch.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(donation, key, value)

    session.commit()
    session.refresh(donation)
    return donation
