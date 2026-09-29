from fastapi import APIRouter, Request, Response, status

from app.api.dependencies import AppSettings, AuthServiceDep, CurrentUser, session_token
from app.schemas.auth import LoginRequest, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=UserRead)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    service: AuthServiceDep,
    settings: AppSettings,
) -> UserRead:
    """Log in with username and password; sets an HttpOnly session cookie."""
    result = service.login(
        username=payload.username,
        password=payload.password,
        client=request.client.host if request.client else "unknown",
    )
    response.set_cookie(
        settings.session_cookie_name,
        result.token,
        max_age=settings.session_days * 24 * 3600,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
    return UserRead.model_validate(result.user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, service: AuthServiceDep, settings: AppSettings) -> Response:
    service.logout(session_token(request, settings))
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
    )
    return response


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser) -> UserRead:
    """The logged-in user; 401 without a valid session."""
    return UserRead.model_validate(user)
