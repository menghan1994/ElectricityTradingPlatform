from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="ElectricityTradingPlatform Agent Engine",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check() -> dict:
    return {
        "status": "ok",
        "service": "agent-engine",
        "llm_model": settings.LLM_MODEL,
    }
