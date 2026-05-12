from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser
from app.core.database import get_db
from app.core.security import (
    create_access_token, create_refresh_token,
    decode_token, hash_password, verify_password,
)
from app.models import User, UserRole   # ✅ IMPORTANT FIX
from app.schemas.schemas import (
    ChangePasswordRequest, LoginRequest,
    RefreshRequest, TokenResponse, UserOut,
)

from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/auth", tags=["Auth"])


# ================= LOGIN =================
@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account deactivated"
        )

    user.last_login = datetime.now(timezone.utc)
    await db.flush()

    sub = str(user.id)
    return TokenResponse(
        access_token=create_access_token({"sub": sub, "role": user.role.value}),
        refresh_token=create_refresh_token({"sub": sub}),
    )


# ================= REFRESH =================
@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    data = decode_token(payload.refresh_token)

    if not data or data.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    result = await db.execute(select(User).where(User.id == UUID(data["sub"])))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    sub = str(user.id)
    return TokenResponse(
        access_token=create_access_token({"sub": sub, "role": user.role.value}),
        refresh_token=create_refresh_token({"sub": sub}),
    )


# ================= ME =================
@router.get("/me", response_model=UserOut)
async def me(current_user: CurrentUser):
    return current_user


# ================= CHANGE PASSWORD =================
@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password incorrect"
        )

    current_user.hashed_password = hash_password(payload.new_password[:72])  # ✅ bcrypt fix
    await db.flush()

    return {"message": "Password changed successfully"}


# ================= REGISTER =================
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str


@router.post("/register")
async def register(
    payload: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        # check existing
        result = await db.execute(select(User).where(User.email == payload.email))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(status_code=400, detail="User already exists")

        # 👇 IMPORTANT: print debug
        print("Creating user...")

        user = User(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
            is_active=True,
            role=UserRole.admin   # keep this
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        print("User created:", user.email)

        return {"message": "User created successfully"}

    except Exception as e:
        print("❌ REGISTER ERROR:", str(e))   # 👈 THIS WILL SHOW REAL ISSUE
        raise HTTPException(status_code=500, detail=str(e))