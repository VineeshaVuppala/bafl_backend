"""
API v1 router aggregation.
"""
from fastapi import APIRouter

from src.api.v1.endpoints import auth, users, permissions


# Create main v1 router
api_v1_router = APIRouter(prefix="/v1")

# Include all endpoint routers
api_v1_router.include_router(auth.router)
api_v1_router.include_router(users.router)
api_v1_router.include_router(permissions.router)
