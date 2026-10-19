"""Точные маршруты Auth из ТЗ; устаревший /api/v1/auth остаётся доступен отдельно."""

from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user, require_gateway
from app.models.user import User
from app.schemas.identity import (
    AccessTokenResponse,
    ChangePasswordBody,
    ForgotPasswordBody,
    IdentityResponse,
    LoginBody,
    LogoutBody,
    ProfilePatch,
    RegisterBody,
    ResendCodeBody,
    ResetPasswordBody,
    VerifyBody,
)
from app.security import create_access_token, decode_token
from app.services.identity_service import IdentityService, UnverifiedAccount

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"], dependencies=[Depends(require_gateway)])
REFRESH_COOKIE = "refresh_token"
VERIFICATION_COOKIE = "verification_challenge"


async def get_identity_service(session: AsyncSession = Depends(get_db)) -> AsyncGenerator[IdentityService, None]:
    service = IdentityService(session)
    try:
        yield service
    finally:
        await service.close()


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=settings.refresh_token_expire_days * 86400,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite="strict",
        path="/auth",
    )


def _set_verification_cookie(response: Response, user_id: int) -> None:
    challenge = create_access_token(user_id, {"type": "verification"})
    response.set_cookie(
        VERIFICATION_COOKIE,
        challenge,
        max_age=settings.verification_code_ttl_seconds,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite="strict",
        path="/auth",
    )


@router.post("/register", response_model=IdentityResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterBody, response: Response, service: IdentityService = Depends(get_identity_service)) -> IdentityResponse:
    user = await service.register(body)
    _set_verification_cookie(response, user.id)
    return IdentityResponse.model_validate(user)


@router.post("/login", response_model=AccessTokenResponse)
async def login(body: LoginBody, request: Request, response: Response, service: IdentityService = Depends(get_identity_service)) -> AccessTokenResponse:
    client_ip = request.client.host if request.client else None
    try:
        _user, access_token, refresh_token = await service.login(body.login, body.password, body.device_info, client_ip)
    except UnverifiedAccount as exc:
        challenge = create_access_token(exc.user_id, {"type": "verification"})
        denied = JSONResponse({"detail": "Verify your email before signing in"}, status_code=403)
        denied.set_cookie(VERIFICATION_COOKIE, challenge, max_age=settings.verification_code_ttl_seconds,
                          httponly=True, secure=settings.refresh_cookie_secure, samesite="strict", path="/auth")
        return denied
    _set_refresh_cookie(response, refresh_token)
    return AccessTokenResponse(access_token=access_token)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(request: Request, response: Response, service: IdentityService = Depends(get_identity_service)) -> AccessTokenResponse:
    access_token, refresh_token = await service.refresh(request.cookies.get(REFRESH_COOKIE))
    _set_refresh_cookie(response, refresh_token)
    return AccessTokenResponse(access_token=access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: LogoutBody, request: Request, response: Response, user: User = Depends(get_current_user), service: IdentityService = Depends(get_identity_service)) -> None:
    await service.revoke_sessions(user, request.cookies.get(REFRESH_COOKIE), body.logout_all_devices)
    response.delete_cookie(REFRESH_COOKIE, path="/auth", httponly=True, secure=settings.refresh_cookie_secure, samesite="strict")


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(body: ChangePasswordBody, user: User = Depends(get_current_user), service: IdentityService = Depends(get_identity_service)) -> None:
    await service.change_password(user, body.current_password, body.new_password)


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(body: ForgotPasswordBody, service: IdentityService = Depends(get_identity_service)) -> dict[str, str]:
    await service.start_password_reset(str(body.email))
    return {"detail": "If the address is registered, reset instructions will be sent"}


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(body: ResetPasswordBody, service: IdentityService = Depends(get_identity_service)) -> None:
    await service.finish_password_reset(body.token_from_email, body.new_password)


@router.post("/verify")
async def verify(body: VerifyBody, response: Response, request: Request, service: IdentityService = Depends(get_identity_service)) -> dict[str, str]:
    if body.type == "phone":
        raise HTTPException(status_code=501, detail="SMS verification is not configured")
    await service.verify_email(body.code)
    response.delete_cookie(VERIFICATION_COOKIE, path="/auth", httponly=True, secure=settings.refresh_cookie_secure, samesite="strict")
    return {"detail": "Email verified"}


@router.post("/resend-code", status_code=status.HTTP_202_ACCEPTED)
async def resend_code(body: ResendCodeBody, request: Request, service: IdentityService = Depends(get_identity_service)) -> dict[str, str]:
    challenge = request.cookies.get(VERIFICATION_COOKIE)
    if not challenge:
        raise HTTPException(status_code=401, detail="Verification challenge is required")
    try:
        claims = decode_token(challenge)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Verification challenge expired") from exc
    if claims.get("type") != "verification":
        raise HTTPException(status_code=401, detail="Invalid verification challenge")
    user = await service.session.get(User, int(claims["sub"]))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await service.resend_code(user, body.type)
    return {"detail": "If verification is required, a new code was sent"}


@router.get("/me", response_model=IdentityResponse)
async def me(user: User = Depends(get_current_user)) -> IdentityResponse:
    return IdentityResponse.model_validate(user)


@router.patch("/me", response_model=IdentityResponse)
async def patch_me(body: ProfilePatch, user: User = Depends(get_current_user), service: IdentityService = Depends(get_identity_service)) -> IdentityResponse:
    updated = await service.patch_profile(user, body)
    return IdentityResponse.model_validate(updated)
