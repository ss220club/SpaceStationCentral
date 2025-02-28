import logging

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.database.models import Admin
from app.deps import SessionDep


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/{id}",
            status_code=status.HTTP_200_OK,
            responses={
                status.HTTP_200_OK: {"description": "Admin"},
                status.HTTP_404_NOT_FOUND: {"description": "Admin not found"},
            })
async def get_admin_by_id(session: SessionDep, id: int) -> Admin:
    result = session.exec(select(Admin).where(Admin.id == id)).first()

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found")

    return result
