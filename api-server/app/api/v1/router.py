from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.bindings import router as bindings_router
from app.api.v1.health import router as health_router
from app.api.v1.stations import router as stations_router
from app.api.v1.users import router as users_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router, tags=["health"])
api_v1_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(users_router, prefix="/users", tags=["users"])
api_v1_router.include_router(stations_router, prefix="/stations", tags=["stations"])
# MEDIUM: 绑定路由使用独立前缀，避免与 users_router 混淆
api_v1_router.include_router(bindings_router, prefix="/bindings", tags=["bindings"])
