from app.routes.v2.player import player_router
from fastapi import APIRouter, status


v2_router = APIRouter(
    prefix="/v2", tags=["v2"], responses={status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"}}
)

routers = [player_router]

for router in routers:
    v2_router.include_router(router)
