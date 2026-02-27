from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import BusinessError
from app.core.logging import setup_logging, TraceIdMiddleware
from app.api.v1.router import api_v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    yield


app = FastAPI(
    title="ElectricityTradingPlatform API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(TraceIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(BusinessError)
async def business_error_handler(request: Request, exc: BusinessError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "detail": exc.detail,
            "trace_id": getattr(request.state, "trace_id", None),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "code": "INTERNAL_ERROR",
            "message": "内部服务器错误",
            "detail": str(exc) if settings.APP_DEBUG else None,
            "trace_id": getattr(request.state, "trace_id", None),
        },
    )


app.include_router(api_v1_router, prefix="/api/v1")
