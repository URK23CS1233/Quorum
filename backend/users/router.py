"""Quorum — Users Router (ADMIN+)"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timezone

from database import get_db
from dependencies import require_admin, require_operator, get_current_user
from db_models import User, UserRole, AuditLog
from auth.schemas import UserOut
from auth.service import hash_password

router = APIRouter(prefix="/api/users", tags=["users"])


class InviteUserRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.VIEWER


class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


def _user_out(u: User, db: Session) -> dict:
    return {
        "id": u.id, "email": u.email, "name": u.name,
        "role": u.role, "org_id": u.org_id,
        "org_name": u.organization.name if u.organization else None,
        "avatar_url": u.avatar_url, "is_active": u.is_active,
        "created_at": str(u.created_at),
        "last_active": str(u.last_active) if u.last_active else None,
    }


@router.get("/", response_model=List[dict])
async def list_users(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    users = db.query(User).filter(User.org_id == current_user.org_id).all()
    return [_user_out(u, db) for u in users]


@router.post("/invite", response_model=dict, status_code=201)
async def invite_user(
    body: InviteUserRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    new_user = User(
        name=body.name, email=body.email,
        hashed_password=hash_password(body.password),
        role=body.role, org_id=current_user.org_id,
    )
    db.add(new_user)

    log = AuditLog(
        user_id=current_user.id, action="user.invite",
        resource=body.email, details=f"Role: {body.role.value}",
    )
    db.add(log)
    db.commit(); db.refresh(new_user)
    return _user_out(new_user, db)


@router.patch("/{user_id}", response_model=dict)
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = db.query(User).filter(
        User.id == user_id, User.org_id == current_user.org_id
    ).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot modify your own role/status")

    changes = []
    if body.name is not None:
        target.name = body.name; changes.append(f"name={body.name}")
    if body.role is not None:
        target.role = body.role; changes.append(f"role={body.role.value}")
    if body.is_active is not None:
        target.is_active = body.is_active; changes.append(f"active={body.is_active}")

    db.add(AuditLog(
        user_id=current_user.id, action="user.update",
        resource=target.email, details=", ".join(changes),
    ))
    db.commit(); db.refresh(target)
    return _user_out(target, db)


@router.delete("/{user_id}")
async def deactivate_user(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = db.query(User).filter(
        User.id == user_id, User.org_id == current_user.org_id
    ).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

    target.is_active = False
    db.add(AuditLog(
        user_id=current_user.id, action="user.deactivate", resource=target.email,
    ))
    db.commit()
    return {"status": "ok", "message": f"{target.name} deactivated"}


@router.get("/audit-log", response_model=List[dict])
async def get_audit_log(
    limit: int = 50,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    logs = (
        db.query(AuditLog)
        .join(User, AuditLog.user_id == User.id, isouter=True)
        .filter(User.org_id == current_user.org_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": l.id, "action": l.action, "resource": l.resource,
            "details": l.details, "created_at": str(l.created_at),
            "user_name": l.user.name if l.user else "System",
            "user_email": l.user.email if l.user else None,
        }
        for l in logs
    ]
