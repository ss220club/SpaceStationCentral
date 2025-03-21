from collections.abc import AsyncIterator

from fastapi import FastAPI, status
from fastapi.concurrency import asynccontextmanager
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import CONFIG
from app.init import init
from app.routes.v1.main_router import v1_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init()
    yield


app = FastAPI(
    title=CONFIG.general.project_name,
    version=CONFIG.general.project_ver,
    description=CONFIG.general.project_desc,
    lifespan=lifespan,
)
app.mount("/nanoui", StaticFiles(directory="app/public/nanoui"), name="nanoui")
app.include_router(v1_router)


@app.get("/", status_code=status.HTTP_301_MOVED_PERMANENTLY)
async def root() -> RedirectResponse:
    return RedirectResponse("/nanoui/index.html")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> FileResponse:
    return FileResponse(CONFIG.general.favicon_path)
