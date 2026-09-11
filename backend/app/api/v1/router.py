"""API v1 router — registers all endpoint groups."""
from fastapi import APIRouter
from app.api.v1.endpoints import complaints, agent

api_router = APIRouter()

api_router.include_router(
    complaints.router,
    prefix="/complaints",
    tags=["Complaints"],
)
api_router.include_router(
    agent.router,
    prefix="/agent",
    tags=["AI Agent"],
)
