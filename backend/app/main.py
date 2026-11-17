from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from pydantic import BaseModel

from app import __version__
from app.core.config import get_settings
from app.features.chat.router import router as chat_router
from app.llm.factory import create_provider


class HealthResponse(BaseModel):
    status: str
    version: str


router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> HealthResponse:
    """Liveness check. Does not touch the model: it must answer even if Ollama is down."""
    return HealthResponse(status="ok", version=__version__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """One provider (and one HTTP connection pool) for the whole life of the server."""
    app.state.provider = create_provider(get_settings())
    try:
        yield
    finally:
        await app.state.provider.aclose()


app = FastAPI(title="AI Lab", version=__version__, lifespan=lifespan)
app.include_router(router)
app.include_router(chat_router)
