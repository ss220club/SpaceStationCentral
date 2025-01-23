from fastapi import APIRouter
from app.routes.v1.player import router as player_router
from app.routes.v1.wl.whitelist import router as whitelist_router

v1_router = APIRouter(prefix="/v1", tags=["v1"])

routers = [
    player_router,
    whitelist_router,
]

for router in routers:
    v1_router.include_router(router)
