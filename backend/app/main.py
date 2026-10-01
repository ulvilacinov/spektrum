from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.api.frontend import mount_frontend
from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    get_settings().upload_dir.mkdir(parents=True, exist_ok=True)
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    if settings.environment == "production" and settings.secret_key is None:
        raise RuntimeError("SECRET_KEY must be set in production (it encrypts the API keys).")
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        debug=settings.debug,
        lifespan=lifespan,
    )
    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)
    if settings.frontend_dist_dir is not None:
        mount_frontend(app, settings.frontend_dist_dir, api_prefix=settings.api_prefix)
    return app


app = create_app()
