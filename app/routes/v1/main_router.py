from fastapi import APIRouter

from app.routes.v1.player import player_router, oauth_router
from app.routes.v1.whitelist import whitelist_router, whitelist_ban_router
from app.routes.v1.donate import router as donate_router

v1_router = APIRouter(prefix="/v1", tags=["v1"])

routers = [
    oauth_router,
    player_router,
    whitelist_router,
    whitelist_ban_router,
    donate_router
]

for router in routers:
    v1_router.include_router(router)
