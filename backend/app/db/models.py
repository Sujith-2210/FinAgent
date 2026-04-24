"""
Database ORM Models
Models for persisting context snapshots, chat history, and audit logs.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean
from sqlalchemy.sql import func
from datetime import datetime

from app.db.database import Base


class User(Base):
    """
    Application user for authentication and ownership of financial context.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class ContextSnapshot(Base):
    """
    Stores snapshots of MCP context for versioning and audit.
    """
    __tablename__ = "context_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    context_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=True, index=True)
    version = Column(Integer, nullable=False)
    context_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=func.now())


class ChatMessage(Base):
    """
    Stores chat messages for history and analysis.
    """
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    agents_involved = Column(JSON, nullable=True)
    reasoning_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now())


class AuditLog(Base):
    """
    Audit log for all context access and agent activity.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=func.now())
    event_type = Column(String(50), nullable=False)  # 'context_read', 'context_write', 'agent_invoke', etc.
    agent = Column(String(50), nullable=True)
    layer = Column(String(50), nullable=True)
    operation = Column(String(20), nullable=True)
    context_version = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    session_id = Column(String(36), nullable=True, index=True)


class Alert(Base):
    """
    Stores generated alerts.
    """
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String(36), nullable=False, unique=True, index=True)
    user_id = Column(String(36), nullable=True, index=True)
    alert_type = Column(String(20), nullable=False)  # 'RISK', 'OPPORTUNITY', 'INFO'
    severity = Column(String(10), nullable=False)  # 'LOW', 'MEDIUM', 'HIGH'
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    triggered_by = Column(String(50), nullable=False)
    status = Column(String(20), default="ACTIVE")  # 'ACTIVE', 'DISMISSED', 'ACKNOWLEDGED'
    context_snapshot = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class UserGoal(Base):
    """
    Stores user-defined financial goals.
    """
    __tablename__ = "user_goals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    goal_id = Column(String(36), nullable=False, unique=True, index=True)
    user_id = Column(String(36), nullable=True, index=True)
    goal_type = Column(String(50), nullable=False)  # 'RETIREMENT', 'EMERGENCY', 'EDUCATION', etc.
    target_horizon = Column(String(20), nullable=False)  # 'SHORT', 'MEDIUM', 'LONG'
    priority = Column(String(10), nullable=False)  # 'LOW', 'MEDIUM', 'HIGH'
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
