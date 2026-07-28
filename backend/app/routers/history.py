"""History endpoint powering the dashboard."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_identity
from ..database import get_db
from ..models import Review, User
from ..schemas import ReviewListItem

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=list[ReviewListItem])
def list_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_identity),
) -> list[ReviewListItem]:
    rows = db.scalars(
        select(Review)
        .where(Review.user_id == user.id)
        .order_by(Review.created_at.desc())
        .limit(min(limit, 200))
    ).all()
    return [
        ReviewListItem(
            id=r.id,
            status=r.status,
            provider=r.provider,
            overall_score=r.overall_score,
            created_at=r.created_at,
            job_description_preview=(r.job_description or "")[:120] or None,
        )
        for r in rows
    ]
