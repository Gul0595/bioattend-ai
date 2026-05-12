from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role not in (UserRole.admin,):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


async def require_hr_or_above(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role not in (UserRole.admin, UserRole.hr, UserRole.manager):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="HR/Admin access required")
    return user


# Dependency aliases
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminOnly   = Annotated[User, Depends(require_admin)]
HROrAbove   = Annotated[User, Depends(require_hr_or_above)]
