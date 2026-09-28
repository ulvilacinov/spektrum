from fastapi import APIRouter

from app.api.routes import chapters, documents, health, learning_sessions, quiz

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(documents.router)
api_router.include_router(chapters.router)
api_router.include_router(learning_sessions.router)
api_router.include_router(quiz.router)
