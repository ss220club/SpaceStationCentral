from logging.config import dictConfig
from app.core.logconfig import log_config
dictConfig(log_config)

import fastapi
from fastapi import FastAPI, status
from fastapi.concurrency import asynccontextmanager
from fastapi.responses import FileResponse

from app.core.config import Config
from app.init import init
from app.routes.player import router as player_router



@asynccontextmanager
async def lifespan(app: FastAPI):
    init()
    yield

app = FastAPI(
    title=Config.General.PROJECT_NAME,
    version=Config.General.PROJECT_VER,
    description=Config.General.PROJECT_DESC,
    lifespan=lifespan)
favicon_path = "app/assets/favicon.png"

app.include_router(player_router)

@app.get("/", status_code=status.HTTP_418_IM_A_TEAPOT)
async def root() -> dict:
    """
    Hello! This is the root of the API. It's teapot-flavored.
    """
    return {"message": "I'm a teapot"}

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(favicon_path)