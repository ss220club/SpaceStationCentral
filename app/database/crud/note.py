import logging

from fastapi import HTTPException, status

from app.database.models import Note
from app.deps import SessionDep


logger = logging.getLogger(__name__)


# region: GET
def get_note(db: SessionDep, note_id: int) -> Note:
    """
    Get note by id.

    Raises:
        HTTPException(404): Note not found
    """
    note = db.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return note


# endregion


# region: POST
def create_note(db: SessionDep, note: Note) -> Note:
    """Create note."""
    db.add(note)
    db.commit()
    logger.info("Created note: %s", note)
    return note


# endregion
