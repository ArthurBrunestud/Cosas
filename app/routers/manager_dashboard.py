from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date, datetime, time, timedelta
from typing import Optional
from app.database import get_db
from app.models import Session, User, Place, PlaceCheckin
from app.dependencies import get_current_manager
from app.schemas import DayReportOut, WorkerReportOut

router = APIRouter()


def default_range(from_date: Optional[date], to_date: Optional[date]) -> tuple[date, date]:
    if from_date is None and to_date is None:
        to_date = datetime.now().date()
        from_date = to_date - timedelta(days=6)
    elif from_date is None:
        from_date = to_date - timedelta(days=6)
    elif to_date is None:
        to_date = datetime.now().date()
    return from_date, to_date


@router.get("/report-by-day", response_model=list[DayReportOut])
async def report_by_day(
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager)
):
    from_date, to_date = default_range(from_date, to_date)

    sessions_result = await db.execute(
        select(Session).where(
            Session.started_at >= datetime.combine(from_date, time.min),
            Session.started_at <= datetime.combine(to_date, time.max)
        )
    )
    sessions = sessions_result.scalars().all()

    checkins_result = await db.execute(
        select(PlaceCheckin, Place.name)
        .join(Place, PlaceCheckin.place_id == Place.id)
        .where(
            PlaceCheckin.checked_in_at >= datetime.combine(from_date, time.min),
            PlaceCheckin.checked_in_at <= datetime.combine(to_date, time.max)
        )
    )
    checkins = checkins_result.all()

    report_by_date: dict[date, DayReportOut] = {}
    current = from_date
    while current <= to_date:
        report_by_date[current] = DayReportOut(
            date=current,
            sessions_started=0,
            total_checkins=0,
            sessions_with_observations=0,
            places_visited_count=0,
            places_visited=[]
        )
        current += timedelta(days=1)

    for session in sessions:
        day = session.started_at.date()
        if day in report_by_date:
            report_by_date[day].sessions_started += 1
            if session.status == "completed_with_observations":
                report_by_date[day].sessions_with_observations += 1

    places_by_day: dict[date, set[str]] = {d: set() for d in report_by_date}
    for checkin, place_name in checkins:
        day = checkin.checked_in_at.date()
        if day in report_by_date:
            report_by_date[day].total_checkins += 1
            places_by_day[day].add(place_name)

    for day, names in places_by_day.items():
        report_by_date[day].places_visited = sorted(names)
        report_by_date[day].places_visited_count = len(names)

    return [report_by_date[d] for d in sorted(report_by_date.keys())]


@router.get("/report-by-worker", response_model=list[WorkerReportOut])
async def report_by_worker(
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager)
):
    from_date, to_date = default_range(from_date, to_date)

    workers_result = await db.execute(
        select(User).where(User.role == "worker")
    )
    workers = workers_result.scalars().all()

    report_by_worker_id: dict[int, WorkerReportOut] = {
        worker.id: WorkerReportOut(
            worker_id=worker.id,
            worker_name=worker.name,
            total_sessions=0,
            total_hours=0.0,
            total_checkins=0
        )
        for worker in workers
    }

    sessions_result = await db.execute(
        select(Session).where(
            Session.started_at >= datetime.combine(from_date, time.min),
            Session.started_at <= datetime.combine(to_date, time.max)
        )
    )
    for session in sessions_result.scalars().all():
        entry = report_by_worker_id.get(session.user_id)
        if entry is None:
            continue
        entry.total_sessions += 1
        if session.total_minutes is not None:
            entry.total_hours += session.total_minutes / 60

    checkins_result = await db.execute(
        select(PlaceCheckin.user_id, func.count())
        .where(
            PlaceCheckin.checked_in_at >= datetime.combine(from_date, time.min),
            PlaceCheckin.checked_in_at <= datetime.combine(to_date, time.max)
        )
        .group_by(PlaceCheckin.user_id)
    )
    for worker_id, count in checkins_result.all():
        entry = report_by_worker_id.get(worker_id)
        if entry is not None:
            entry.total_checkins = count

    for entry in report_by_worker_id.values():
        entry.total_hours = round(entry.total_hours, 2)

    return sorted(report_by_worker_id.values(), key=lambda e: e.worker_name)