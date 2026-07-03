"""Quorum — Auth Router"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from database import get_db
from dependencies import get_current_user
from db_models import User
from auth.schemas import (
    RegisterRequest, LoginRequest, TokenResponse,
    RefreshRequest, UserOut, ChangePasswordRequest, UpdateProfileRequest,
)
import auth.service as svc

router  = APIRouter(prefix="/api/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=TokenResponse, status_code=201)
@limiter.limit("5/minute")
async def register(request: Request, body: RegisterRequest, db: Session = Depends(get_db)):
    user = svc.register(body.name, body.email, body.password, body.org_name, db)
    return TokenResponse(
        access_token=svc.create_access_token(user),
        refresh_token=svc.create_refresh_token(user, db),
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    user = svc.login(body.email, body.password, db)
    return TokenResponse(
        access_token=svc.create_access_token(user),
        refresh_token=svc.create_refresh_token(user, db),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    user = svc.refresh_access_token(body.refresh_token, db)
    return TokenResponse(
        access_token=svc.create_access_token(user),
        refresh_token=svc.create_refresh_token(user, db),
    )


@router.post("/logout")
async def logout(body: RefreshRequest, db: Session = Depends(get_db)):
    svc.logout(body.refresh_token, db)
    return {"status": "ok"}


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    org_name = current_user.organization.name if current_user.organization else None
    return UserOut(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        org_id=current_user.org_id,
        org_name=org_name,
        avatar_url=current_user.avatar_url,
        is_active=current_user.is_active,
        created_at=str(current_user.created_at),
        last_active=str(current_user.last_active) if current_user.last_active else None,
    )


@router.put("/me", response_model=UserOut)
async def update_profile(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.name:        current_user.name = body.name
    if body.avatar_url:  current_user.avatar_url = body.avatar_url
    db.commit(); db.refresh(current_user)
    return await me(current_user, db)


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not svc.verify_password(body.current_password, current_user.hashed_password):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Current password incorrect")
    current_user.hashed_password = svc.hash_password(body.new_password)
    db.commit()
    return {"status": "ok", "message": "Password changed successfully"}
