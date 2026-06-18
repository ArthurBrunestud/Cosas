from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date, datetime, time
from typing import Optional
from app.database import get_db
from app.models import Session, User, Place, SystemEventLog
from app.dependencies import get_current_manager
from app.schemas import SessionHistoryOut

router = APIRouter()


@router.get("/", response_model=list[SessionHistoryOut])
async def get_sessions_history(
    worker_id: Optional[int] = Query(None),
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager)
):
    query = (
        select(Session, User.name, Place.name)
        .join(User, Session.user_id == User.id)
        .join(Place, Session.place_id == Place.id)
        .where(Session.status != "active")
    )

    if worker_id is not None:
        query = query.where(Session.user_id == worker_id)
    if from_date is not None:
        query = query.where(Session.started_at >= datetime.combine(from_date, time.min))
    if to_date is not None:
        query = query.where(Session.started_at <= datetime.combine(to_date, time.max))

    query = query.order_by(Session.started_at.desc()).limit(limit)

    result = await db.execute(query)
    rows = result.all()
    return [
        SessionHistoryOut(
            id=session.id,
            worker_id=session.user_id,
            worker_name=worker_name,
            place_name=place_name,
            started_at=session.started_at,
            ended_at=session.ended_at,
            total_minutes=session.total_minutes,
            status=session.status
        )
        for session, worker_name, place_name in rows
    ]

