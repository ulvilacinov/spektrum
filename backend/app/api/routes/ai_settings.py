from fastapi import APIRouter, status

from app.api.dependencies import AISettingsServiceDep, CurrentUserId
from app.schemas.ai_settings import AIDraftIn, AIModelsRead, AISettingsRead, AITestRead

router = APIRouter(prefix="/ai-settings", tags=["ai settings"])


@router.get("", response_model=AISettingsRead)
def get_ai_settings(user_id: CurrentUserId, service: AISettingsServiceDep) -> AISettingsRead:
    """The user's AI provider and model; the API key is never returned."""
    return AISettingsRead.from_settings(service.get(user_id))


@router.put("", response_model=AISettingsRead)
def save_ai_settings(
    payload: AIDraftIn, user_id: CurrentUserId, service: AISettingsServiceDep
) -> AISettingsRead:
    """Save provider, model and key (stored encrypted). Omit the key to keep the saved one."""
    return AISettingsRead.from_settings(service.save(user_id, payload.to_draft()))


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_ai_settings(user_id: CurrentUserId, service: AISettingsServiceDep) -> None:
    """Forget the key; AI features stop until a new one is saved."""
    service.delete(user_id)


@router.post("/models", response_model=AIModelsRead)
def list_models(
    payload: AIDraftIn, user_id: CurrentUserId, service: AISettingsServiceDep
) -> AIModelsRead:
    """Models the (entered or saved) key can use."""
    return AIModelsRead(models=service.list_models(user_id, payload.to_draft()))


@router.post("/test", response_model=AITestRead)
def test_connection(
    payload: AIDraftIn, user_id: CurrentUserId, service: AISettingsServiceDep
) -> AITestRead:
    """Send one tiny request with these settings (nothing is saved)."""
    return AITestRead(reply=service.test(user_id, payload.to_draft()))
