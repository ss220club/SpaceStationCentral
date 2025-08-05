from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_config
from app.core.exceptions import EntityNotFoundError
from app.routes.v1.main_router import v1_router
from app.routes.v2.main_router import v2_router


app = FastAPI(
    title=get_config().general.name,
    version=get_config().general.version,
    description=get_config().general.description,
)


@app.exception_handler(EntityNotFoundError)
async def entity_not_found_handler(_: Request, exc: EntityNotFoundError) -> HTTPException:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


app.mount("/nanoui", StaticFiles(directory="app/public/nanoui"), name="nanoui")
app.include_router(v1_router)
app.include_router(v2_router)


@app.get("/", status_code=status.HTTP_301_MOVED_PERMANENTLY)
async def root() -> RedirectResponse:
    return RedirectResponse("/nanoui/index.html")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> FileResponse:
    return FileResponse(get_config().general.favicon_path)
