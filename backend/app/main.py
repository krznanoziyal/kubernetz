import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .api.router import router

settings = get_settings()

logging.basicConfig(level=settings.log_level)
log = logging.getLogger(__name__)

app = FastAPI(
    title="KubeBlueprint API",
    description="Convert Kubernetes architecture diagrams into validated project scaffolds.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/health", tags=["infra"])
async def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}
