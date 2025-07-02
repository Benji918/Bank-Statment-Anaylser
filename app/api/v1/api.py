"""API v1 router configuration"""

from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, statements, analyses, health

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(statements.router, prefix="/statements", tags=["statements"])
api_router.include_router(analyses.router, prefix="/analyses", tags=["analyses"])
api_router.include_router(health.router, prefix="/health", tags=["health"])