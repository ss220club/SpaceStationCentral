import logging
logger = logging.getLogger("main-logger")


from app.database.models import Player, Whitelist
from app.schemas.whitelist import NewWhitelist
from app.deps import SessionDep, verify_bearer

from sqlmodel import select
from fastapi import APIRouter, Depends, status


router = APIRouter(prefix="/whitelist", tags=["Whitelist"])
@router.post("/", dependencies=[Depends(verify_bearer)], status_code=status.HTTP_201_CREATED)
def create_whitelist(session: SessionDep, new_wl: NewWhitelist) -> Whitelist:
    wl = Whitelist.model_validate(new_wl)
    session.add(wl)
    session.commit()
    session.refresh(wl)
    return wl

@router.get("/ckey/{ckey}", status_code=status.HTTP_200_OK)
async def get_whitelist_by_ckey(session: SessionDep, ckey: str, valid: bool = True) -> list[Whitelist]:
    result = session.exec(select(Whitelist).join(Player, onclause=Player.discord_id == Whitelist.player_id).where(Player.ckey == ckey and Whitelist.valid == valid))
    return result.all()
