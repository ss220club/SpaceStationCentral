import logging

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Note


logger = logging.getLogger(__name__)


# region: GET
async def get_note(db: AsyncSession, note_id: int) -> Note:
    """
    Get note by id

    Raises:
        HTTPException(404): Note not found
    """
    note = await db.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return note


# endregion


# region: POST
async def create_note(db: AsyncSession, note: Note) -> Note:
    """
    Create note
    """
    db.add(note)
    await db.commit()
    logger.info("Created note: %s", note)
    return note


# endregion
