"""Role-based access control (RBAC) — backend enforcement"""

from functools import wraps
from typing import List
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth.jwt import decode_token
from app.db.database import get_db
from app.models.user import User, UserRole

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate the current user from JWT token."""
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен авторизации",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен авторизации",
        )

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден или деактивирован",
        )

    return user


def require_roles(allowed_roles: List[UserRole]):
    """Dependency that checks if the current user has one of the allowed roles.
    
    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(user: User = Depends(require_roles([UserRole.OWNER]))):
            ...
    """
    async def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для выполнения этого действия",
            )
        return current_user

    return role_checker


# Convenience shortcuts
require_owner = require_roles([UserRole.OWNER])
require_owner_or_manager = require_roles([UserRole.OWNER, UserRole.MANAGER])
require_any_role = require_roles([UserRole.OWNER, UserRole.MANAGER, UserRole.EMPLOYEE])
