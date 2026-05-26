from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from config import ACCESS_TOKEN_EXPIRE_MINUTES, COOKIE_NAME, JWT_ALGORITHM, JWT_SECRET, USERS_DB_PATH
from models.schemas import UserOut

from access_control import UserRecord, get_role_indexes, get_user


bearer_scheme = HTTPBearer(auto_error=False)


def create_access_token(user: UserRecord) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user.username,
        "role": user.role,
        "firm_id": user.firm_id,
        "exp": expires_at,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def serialize_user(user: UserRecord) -> UserOut:
    return UserOut(
        username=user.username,
        role=user.role,
        firm_id=user.firm_id,
        corpora=get_role_indexes(user.role, user.firm_id),
    )


def _token_from_request(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
) -> str | None:
    if credentials:
        return credentials.credentials
    return request.cookies.get(COOKIE_NAME)


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> UserRecord:
    token = _token_from_request(request, credentials)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username = str(payload.get("sub") or "")
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    user = get_user(username, db_path=str(USERS_DB_PATH))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")
    return user


def require_roles(*allowed_roles: str):
    allowed = {role.lower() for role in allowed_roles}

    async def dependency(user: Annotated[UserRecord, Depends(get_current_user)]) -> UserRecord:
        if user.role.lower() not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return dependency

