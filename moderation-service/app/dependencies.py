import hmac
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import get_settings

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)


async def require_gateway(request: Request) -> None:
    supplied = request.headers.get("X-Gateway-Token", "")
    if not hmac.compare_digest(supplied, settings.gateway_shared_secret):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API Gateway required")


async def require_moderator(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if request.headers.get("X-Authenticated-User-Role") != "moderator" or credentials is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Moderator role required")
    try:
        claims = jwt.decode(credentials.credentials, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc
    if claims.get("type") != "access" or claims.get("role") != "moderator":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Moderator role required")
    try:
        claims["moderator_id"] = claims.get("user_id") or claims.get("sub")
        claims["moderator_id"] = UUID(str(claims["moderator_id"]))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has no user identity") from exc
    return claims

