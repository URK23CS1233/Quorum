"""Quorum — FastAPI Dependencies (auth + RBAC)"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from datetime import datetime, timezone

from database import get_db
from db_models import User, UserRole, ROLE_HIERARCHY
from config import get_settings

settings  = get_settings()
bearer    = HTTPBearer(auto_error=False)


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = _decode_token(credentials.credentials)
    user_id: str = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found or deactivated")

    # Update last_active
    user.last_active = datetime.now(timezone.utc)
    db.commit()
    return user


def require_role(min_role: UserRole):
    """Dependency factory: require at least this role level."""
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        user_level = ROLE_HIERARCHY.get(current_user.role, 0)
        min_level  = ROLE_HIERARCHY.get(min_role, 0)
        if user_level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role {min_role.value} or higher. Your role: {current_user.role.value}",
            )
        return current_user
    return _check


# Convenience shorthands
require_viewer   = require_role(UserRole.VIEWER)
require_analyst  = require_role(UserRole.ANALYST)
require_operator = require_role(UserRole.OPERATOR)
require_admin    = require_role(UserRole.ADMIN)
require_super    = require_role(UserRole.SUPER_ADMIN)
