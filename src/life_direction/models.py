"""Life direction data models for APA-OS."""

from sqlalchemy import Column, String, DateTime, JSON, Enum, ForeignKey, Integer, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum
import uuid

from database.models import Base


class GoalStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class FutureSelfModel(Base):
    """Defines a user's aspirational future self."""
    __tablename__ = "future_self_models"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(255), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    categories = Column(JSON, default=list)
    target_date = Column(DateTime, nullable=True)
    status = Column(Enum(GoalStatus), default=GoalStatus.ACTIVE, index=True)
    progress = Column(JSON, default=dict)
    meta_info = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LifeGoal(Base):
    """A goal that contributes to a future self model."""
    __tablename__ = "life_goals"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    future_self_id = Column(String(36), ForeignKey("future_self_models.id"), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(Integer, default=1)
    target_date = Column(DateTime, nullable=True)
    status = Column(Enum(GoalStatus), default=GoalStatus.ACTIVE, index=True)
    progress = Column(Float, default=0.0)
    metrics = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RealityCheck(Base):
    """Daily reality check for alignment to future self goals."""
    __tablename__ = "reality_checks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(255), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    goal_alignment_score = Column(Float, nullable=False)
    time_spent = Column(JSON, default=dict)
    summary = Column(Text, nullable=True)
    insights = Column(JSON, default=dict)
    recommendations = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
