from fastapi import APIRouter, FastAPI
from pydantic import BaseModel

from app import __version__


class HealthResponse(BaseModel):
    status: str
    version: str


router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> HealthResponse:
    """Liveness check. Does not touch the model: it must answer even if Ollama is down."""
    return HealthResponse(status="ok", version=__version__)


app = FastAPI(title="AI Lab", version=__version__)
app.include_router(router)
