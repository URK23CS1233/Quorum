"""Quorum — Auth Pydantic Schemas"""

from pydantic import BaseModel, EmailStr
from typing import Optional
from db_models import UserRole


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    org_name: str  # First user creates the org


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    role: UserRole
    org_id: str
    org_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    created_at: str
    last_active: Optional[str] = None

    class Config:
        from_attributes = True


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None
