from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user_id
from app.api.routes import (
    ai_settings,
    auth,
    chapters,
    chat,
    documents,
    health,
    learning_sessions,
    progress,
    quiz,
)

api_router = APIRouter()
# Open: health checks and logging in.
api_router.include_router(health.router)
api_router.include_router(auth.router)

# Everything else needs a logged-in user.
_login_required = [Depends(get_current_user_id)]
for protected in (documents, chapters, learning_sessions, quiz, progress, chat, ai_settings):
    api_router.include_router(protected.router, dependencies=_login_required)
