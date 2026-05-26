from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from auth import COOKIE_NAME, create_access_token, get_current_user, serialize_user
from config import ACCESS_TOKEN_EXPIRE_MINUTES, COOKIE_SECURE, USERS_DB_PATH
from models.schemas import LoginRequest, LoginResponse, UserOut

from access_control import UserRecord, authenticate_user


router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=LoginResponse)
async def login(payload: LoginRequest, response: Response) -> LoginResponse:
    user = authenticate_user(payload.username, payload.password, db_path=str(USERS_DB_PATH))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    token = create_access_token(user)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    return LoginResponse(access_token=token, user=serialize_user(user))


@router.post("/auth/logout")
async def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/user/me", response_model=UserOut)
async def me(user: UserRecord = Depends(get_current_user)) -> UserOut:
    return serialize_user(user)
