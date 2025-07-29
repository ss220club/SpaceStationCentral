import logging

from sqlmodel import Session

from app.core.exceptions import EntityNotFoundError
from app.database.models import Note


logger = logging.getLogger(__name__)


# region: GET
def get_note(db: Session, note_id: int) -> Note:
    """Get note by id."""
    note = db.get(Note, note_id)
    if note is None:
        raise EntityNotFoundError("Note not found")
    return note


# endregion


# region: POST
def create_note(db: Session, note: Note) -> Note:
    """Create note."""
    db.add(note)
    db.commit()
    logger.info("Created note: %s", note)
    return note


# endregion
