"""Life direction engine implementation for APA-OS."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from database.connection import get_db_session
from life_direction.models import FutureSelfModel, LifeGoal, RealityCheck, GoalStatus


class LifeDirectionEngine:
    """Engine for future self planning, reality checks, and recommendations."""

    def __init__(self, session=None):
        self.session = session or get_db_session()

    def create_future_self_model(
        self,
        user_id: str,
        title: str,
        description: Optional[str] = None,
        categories: Optional[List[str]] = None,
        target_date: Optional[datetime] = None,
    ) -> FutureSelfModel:
        """Create a new future self model for a user."""
        model = FutureSelfModel(
            user_id=user_id,
            title=title,
            description=description,
            categories=categories or [],
            target_date=target_date,
            status=GoalStatus.ACTIVE,
            progress={"alignment": 0.0, "skills": {}, "projects": {}},
            meta_info={"created_by": user_id},
        )

        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return model

    def list_future_self_models(self, user_id: str) -> List[FutureSelfModel]:
        """Return all future self models for a user."""
        return self.session.query(FutureSelfModel).filter(FutureSelfModel.user_id == user_id).all()

    def add_life_goal(
        self,
        future_self_id: str,
        user_id: str,
        title: str,
        description: Optional[str] = None,
        priority: int = 1,
        target_date: Optional[datetime] = None,
    ) -> LifeGoal:
        """Add a goal under a future self model."""
        goal = LifeGoal(
            future_self_id=future_self_id,
            user_id=user_id,
            title=title,
            description=description,
            priority=priority,
            target_date=target_date,
            status=GoalStatus.ACTIVE,
            progress=0.0,
            metrics={"history": []},
        )

        self.session.add(goal)
        self.session.commit()
        self.session.refresh(goal)
        return goal

    def list_goals(self, user_id: str, future_self_id: Optional[str] = None) -> List[LifeGoal]:
        """List life goals by user and optionally by future self model."""
        query = self.session.query(LifeGoal).filter(LifeGoal.user_id == user_id)
        if future_self_id:
            query = query.filter(LifeGoal.future_self_id == future_self_id)
        return query.order_by(LifeGoal.priority.desc(), LifeGoal.created_at.asc()).all()

    def create_reality_check(
        self,
        user_id: str,
        date: Optional[datetime] = None,
        time_spent: Optional[Dict[str, float]] = None,
        summary: Optional[str] = None,
        insights: Optional[Dict[str, Any]] = None,
    ) -> RealityCheck:
        """Create a daily reality check with alignment metrics."""
        date = date or datetime.utcnow()
        time_spent = time_spent or {}
        insights = insights or {}

        alignment_score = self._calculate_alignment_score(time_spent)
        recommendations = self._generate_recommendations(time_spent, summary)

        reality_check = RealityCheck(
            user_id=user_id,
            date=date,
            goal_alignment_score=alignment_score,
            time_spent=time_spent,
            summary=summary,
            insights=insights,
            recommendations=recommendations,
        )

        self.session.add(reality_check)
        self.session.commit()
        self.session.refresh(reality_check)
        return reality_check

    def get_reality_checks(self, user_id: str, date: Optional[datetime] = None) -> List[RealityCheck]:
        """Return reality checks for the user."""
        query = self.session.query(RealityCheck).filter(RealityCheck.user_id == user_id)
        if date is not None:
            start = datetime(date.year, date.month, date.day)
            end = start + timedelta(days=1)
            query = query.filter(RealityCheck.date >= start, RealityCheck.date < end)
        return query.order_by(RealityCheck.date.desc()).all()

    def recommend_next_action(self, user_id: str) -> Dict[str, Any]:
        """Return a next-best-action recommendation for the user."""
        recent_checks = self.get_reality_checks(user_id)
        goals = self.list_goals(user_id)
        score = recent_checks[0].goal_alignment_score if recent_checks else 0.0

        if score < 0.4:
            recommendation = "Focus on the highest-priority goal and reduce low-impact screen time."
        elif score < 0.7:
            recommendation = "Double down on consistent practice for your current top skill."
        else:
            recommendation = "Maintain momentum and review the next milestone for your mission."

        if goals:
            top_goal = goals[0]
            recommendation += f" Start by making measurable progress on: {top_goal.title}."

        return {
            "user_id": user_id,
            "alignment_score": score,
            "recommendation": recommendation,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def _calculate_alignment_score(self, time_spent: Dict[str, float]) -> float:
        """Calculate a simple reality check score based on time allocation."""
        learning = time_spent.get("learning", 0.0)
        work = time_spent.get("work", 0.0)
        rest = time_spent.get("rest", 0.0)
        distractions = time_spent.get("distractions", 0.0)

        total = learning + work + rest + distractions
        if total <= 0:
            return 0.0

        alignment = (learning + work * 0.5) / total
        penalty = min(distractions / total, 0.3)
        score = max(0.0, min(1.0, alignment - penalty))
        return round(score, 3)

    def _generate_recommendations(self, time_spent: Dict[str, float], summary: Optional[str]) -> Dict[str, Any]:
        """Generate simple recommendation signals from time allocation."""
        recommendations = {}
        if time_spent.get("learning", 0) < 1.0:
            recommendations["learning"] = "Increase focused learning time by at least 1 hour."
        if time_spent.get("distractions", 0) > 1.5:
            recommendations["distractions"] = "Limit distractions and switch to deep work blocks."
        if summary and "stress" in summary.lower():
            recommendations["wellbeing"] = "Take a short recovery break and re-evaluate priorities."
        return recommendations


_life_direction_engine = None


def get_life_direction_engine(session=None) -> LifeDirectionEngine:
    global _life_direction_engine
    if _life_direction_engine is None or session is not None:
        _life_direction_engine = LifeDirectionEngine(session=session)
    return _life_direction_engine
