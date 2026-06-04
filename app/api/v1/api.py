from fastapi import APIRouter
from app.api.v1.endpoints import ai_chat

api_router = APIRouter()

# Register the chat endpoint sub-router under /ai
api_router.include_router(ai_chat.router, prefix="/ai", tags=["AI Strategy"])