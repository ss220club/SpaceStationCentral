from fastapi import APIRouter, status

from app.routes.v1.donate import router as donate_router
from app.routes.v1.player import oauth_router, player_router
from app.routes.v1.whitelist import whitelist_ban_router, whitelist_router


v1_router = APIRouter(
    prefix="/v1", tags=["v1"], responses={status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"}}
)

routers = [oauth_router, player_router, whitelist_router, whitelist_ban_router, donate_router]

for router in routers:
    v1_router.include_router(router)
