"""API routes for APA-OS life direction features."""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List, Dict, Any
from datetime import datetime

from database.connection import get_db_session
from life_direction.engine import get_life_direction_engine
from life_direction.models import GoalStatus

router = APIRouter(prefix="/life_direction", tags=["Life Direction"])


@router.post("/future_self")
async def create_future_self(
    user_id: str,
    title: str,
    description: Optional[str] = None,
    categories: Optional[List[str]] = Query(None),
    target_date: Optional[datetime] = None,
    session=Depends(get_db_session),
) -> Dict[str, Any]:
    engine = get_life_direction_engine(session=session)
    model = engine.create_future_self_model(
        user_id=user_id,
        title=title,
        description=description,
        categories=categories,
        target_date=target_date,
    )

    return {
        "id": model.id,
        "user_id": model.user_id,
        "title": model.title,
        "description": model.description,
        "categories": model.categories,
        "target_date": model.target_date.isoformat() if model.target_date else None,
        "status": model.status.value,
        "progress": model.progress,
    }


@router.get("/future_self", response_model=List[Dict[str, Any]])
async def list_future_self(
    user_id: str,
    session=Depends(get_db_session),
) -> List[Dict[str, Any]]:
    engine = get_life_direction_engine(session=session)
    models = engine.list_future_self_models(user_id=user_id)
    return [
        {
            "id": model.id,
            "user_id": model.user_id,
            "title": model.title,
            "description": model.description,
            "categories": model.categories,
            "target_date": model.target_date.isoformat() if model.target_date else None,
            "status": model.status.value,
            "progress": model.progress,
        }
        for model in models
    ]


@router.post("/goals")
async def add_life_goal(
    future_self_id: str,
    user_id: str,
    title: str,
    description: Optional[str] = None,
    priority: int = 1,
    target_date: Optional[datetime] = None,
    status: GoalStatus = GoalStatus.ACTIVE,
    session=Depends(get_db_session),
) -> Dict[str, Any]:
    engine = get_life_direction_engine(session=session)
    goal = engine.add_life_goal(
        future_self_id=future_self_id,
        user_id=user_id,
        title=title,
        description=description,
        priority=priority,
        target_date=target_date,
    )
    return {
        "id": goal.id,
        "future_self_id": goal.future_self_id,
        "user_id": goal.user_id,
        "title": goal.title,
        "description": goal.description,
        "priority": goal.priority,
        "target_date": goal.target_date.isoformat() if goal.target_date else None,
        "status": goal.status.value,
        "progress": goal.progress,
    }


@router.get("/goals")
async def list_goals(
    user_id: str,
    future_self_id: Optional[str] = None,
    session=Depends(get_db_session),
) -> List[Dict[str, Any]]:
    engine = get_life_direction_engine(session=session)
    goals = engine.list_goals(user_id=user_id, future_self_id=future_self_id)
    return [
        {
            "id": goal.id,
            "future_self_id": goal.future_self_id,
            "user_id": goal.user_id,
            "title": goal.title,
            "description": goal.description,
            "priority": goal.priority,
            "target_date": goal.target_date.isoformat() if goal.target_date else None,
            "status": goal.status.value,
            "progress": goal.progress,
            "metrics": goal.metrics,
        }
        for goal in goals
    ]


@router.post("/reality_check")
async def create_reality_check(
    user_id: str,
    date: Optional[datetime] = None,
    time_spent: Optional[Dict[str, float]] = None,
    summary: Optional[str] = None,
    insights: Optional[Dict[str, Any]] = None,
    session=Depends(get_db_session),
) -> Dict[str, Any]:
    engine = get_life_direction_engine(session=session)
    reality_check = engine.create_reality_check(
        user_id=user_id,
        date=date,
        time_spent=time_spent,
        summary=summary,
        insights=insights,
    )
    return {
        "id": reality_check.id,
        "user_id": reality_check.user_id,
        "date": reality_check.date.isoformat(),
        "goal_alignment_score": reality_check.goal_alignment_score,
        "time_spent": reality_check.time_spent,
        "summary": reality_check.summary,
        "insights": reality_check.insights,
        "recommendations": reality_check.recommendations,
    }


@router.get("/reality_check")
async def get_reality_checks(
    user_id: str,
    date: Optional[datetime] = None,
    session=Depends(get_db_session),
) -> List[Dict[str, Any]]:
    engine = get_life_direction_engine(session=session)
    checks = engine.get_reality_checks(user_id=user_id, date=date)
    return [
        {
            "id": check.id,
            "user_id": check.user_id,
            "date": check.date.isoformat(),
            "goal_alignment_score": check.goal_alignment_score,
            "time_spent": check.time_spent,
            "summary": check.summary,
            "insights": check.insights,
            "recommendations": check.recommendations,
        }
        for check in checks
    ]


@router.get("/recommendation")
async def recommendation(user_id: str, session=Depends(get_db_session)) -> Dict[str, Any]:
    engine = get_life_direction_engine(session=session)
    return engine.recommend_next_action(user_id=user_id)
