"""Quorum — SQLAlchemy ORM Models"""

import uuid
import enum
from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey,
    Text, Integer, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN       = "ADMIN"
    OPERATOR    = "OPERATOR"
    ANALYST     = "ANALYST"
    VIEWER      = "VIEWER"


ROLE_HIERARCHY = {
    UserRole.SUPER_ADMIN: 5,
    UserRole.ADMIN:       4,
    UserRole.OPERATOR:    3,
    UserRole.ANALYST:     2,
    UserRole.VIEWER:      1,
}


class Organization(Base):
    __tablename__ = "organizations"

    id         = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name       = Column(String, nullable=False)
    slug       = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    users        = relationship("User",       back_populates="organization")
    data_sources = relationship("DataSource", back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id              = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email           = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    name            = Column(String, nullable=False)
    role            = Column(SAEnum(UserRole), default=UserRole.VIEWER, nullable=False)
    org_id          = Column(String, ForeignKey("organizations.id"), nullable=False)
    is_active       = Column(Boolean, default=True)
    avatar_url      = Column(String, nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    last_active     = Column(DateTime(timezone=True), nullable=True)

    organization   = relationship("Organization",  back_populates="users")
    refresh_tokens = relationship("RefreshToken",  back_populates="user", cascade="all, delete")
    conversations  = relationship("Conversation",  back_populates="user", cascade="all, delete")
    audit_logs     = relationship("AuditLog",      back_populates="user")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id         = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    token      = Column(String, unique=True, nullable=False, index=True)
    user_id    = Column(String, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="refresh_tokens")


class DataSource(Base):
    __tablename__ = "data_sources"

    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id      = Column(String, ForeignKey("organizations.id"), nullable=False)
    name        = Column(String, nullable=False)
    source_type = Column(String, nullable=False)  # github | pagerduty | datadog | slack | manual
    config      = Column(Text, nullable=True)     # JSON (tokens, URLs — plaintext for demo; encrypt in prod)
    is_active   = Column(Boolean, default=True)
    last_sync   = Column(DateTime(timezone=True), nullable=True)
    sync_count  = Column(Integer, default=0)
    created_by  = Column(String, ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    organization = relationship("Organization", back_populates="data_sources")


class Conversation(Base):
    __tablename__ = "conversations"

    id         = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id    = Column(String, ForeignKey("users.id"), nullable=False)
    title      = Column(String, default="New conversation")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user     = relationship("User",    back_populates="conversations")
    messages = relationship(
        "Message", back_populates="conversation",
        cascade="all, delete", order_by="Message.created_at"
    )


class Message(Base):
    __tablename__ = "messages"

    id              = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    role            = Column(String, nullable=False)   # user | assistant
    content         = Column(Text, nullable=False)
    tokens_used     = Column(Integer, default=0)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    conversation = relationship("Conversation", back_populates="messages")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id         = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id    = Column(String, ForeignKey("users.id"), nullable=True)
    action     = Column(String, nullable=False)
    resource   = Column(String, nullable=True)
    details    = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="audit_logs")
