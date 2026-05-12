"""
BioAttend Ultimate — Password Reset Flow
MEDIUM gap fix: forgot password email + token-based reset
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import hash_password
from app.models import PasswordResetToken, User

router = APIRouter(prefix="/auth", tags=["Auth"])


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/forgot-password", response_model=dict)
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Send a password reset link to the given email.
    Always returns 200 (even if email not found) to prevent user enumeration.
    """
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if user and user.is_active:
        # Generate a cryptographically secure token
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        reset = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        )
        db.add(reset)
        await db.flush()

        # Send reset email in background
        import asyncio
        from app.services.notification_service import send_password_reset
        from app.core.config import settings
        frontend_url = settings.CORS_ORIGINS.split(",")[0].strip()
        asyncio.create_task(send_password_reset(
            email=user.email,
            name=user.full_name,
            reset_token=raw_token,
            frontend_url=frontend_url,
        ))

    return {"message": "If this email is registered, a reset link has been sent. Check your inbox."}


@router.post("/reset-password", response_model=dict)
async def reset_password(
    payload: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Reset password using the token received by email."""
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used == False,
            PasswordResetToken.expires_at > datetime.now(timezone.utc),
        )
    )
    reset = result.scalar_one_or_none()

    if not reset:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset token. Please request a new reset link.",
        )

    # Update password
    user_result = await db.execute(select(User).where(User.id == reset.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = hash_password(payload.new_password)
    reset.used = True
    await db.flush()

    return {"message": "Password reset successfully. You can now log in with your new password."}
