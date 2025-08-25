import logging
from contextlib import asynccontextmanager

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from fastapi import FastAPI

from fastapi_versionizer.versionizer import Versionizer
from sqlalchemy.ext.asyncio import create_async_engine
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request

from app.api import api_router

__config_path__ = "alembic.ini"

from app.core import get_vault_id

cfg = AlembicConfig(__config_path__)

async def migrate_db():
    conn_url = cfg.get_main_option("sqlalchemy.url")
    async_engine = create_async_engine(conn_url, echo=True)
    async with async_engine.begin() as conn:
        await conn.run_sync(__execute_upgrade)


def __execute_upgrade(connection):
    cfg.attributes["connection"] = connection
    alembic_command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log = logging.getLogger("uvicorn")
    log.info("Starting up...")
    log.info("Run alembic upgrade head...")
    await migrate_db()
    log.info("Finished alembic upgrade head")
    yield
    log.info("Shutting down...")

app = FastAPI(
    root_path='',
    title='Beshence Vault',
    description='Beshence Vault',
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

api_versions = Versionizer(
    app=app,
    default_version=(1, 0),
    prefix_format='/api/v{major}.{minor}',
    semantic_version_format='{major}.{minor}',
    latest_prefix='/api/latest',
    sort_routes=True,
    include_main_docs=False,
    include_main_openapi_route=False
).versionize()

app.state.versions = ["v"+".".join(map(str, api_version)) for api_version in api_versions]

# TODO: move somewhere
@app.get('/.well-known/beshence/vault', tags=['Common'])
async def well_known(request: Request):
    return {
        "id": get_vault_id(),
        "api": {
            # TODO: automatic generation of addresses as well as manual editing them in settings
            "addresses": ["https://127.0.0.1:443/api"],
            "versions": request.app.state.versions
        }
    }