from logging.config import dictConfig

from fastapi import FastAPI, status
from fastapi.concurrency import asynccontextmanager
from fastapi.responses import FileResponse

from app.core.config import Config
from app.core.logconfig import log_config
from app.init import init
from app.routes.player import router as player_router
from app.routes.wl.whitelist import router as whitelist_router
from app.routes.wl.whitelistban import router as whitelistban_router

dictConfig(log_config)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init()
    yield

app = FastAPI(
    title=Config.General.PROJECT_NAME,
    version=Config.General.PROJECT_VER,
    description=Config.General.PROJECT_DESC,
    lifespan=lifespan
)

routers = [
    player_router,
    whitelist_router,
    whitelistban_router
]
for router in routers:
    app.include_router(router)


@app.get("/", status_code=status.HTTP_418_IM_A_TEAPOT)
async def root() -> dict:
    """
    Hello! This is the root of the API. It's teapot-flavored.
    """
    return {"message": "I'm a teapot"}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(Config.General.FAVICON_PATH)
