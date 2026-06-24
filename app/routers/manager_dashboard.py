from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date, datetime, time, timedelta
from typing import Optional
from app.database import get_db
from app.models import Session, User
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
            Session.started_at <= datetime.combine(to_date, time.max),
            Session.status != "active"
        )
    )
    sessions = sessions_result.scalars().all()

    report: dict[date, DayReportOut] = {}
    current = from_date
    while current <= to_date:
        report[current] = DayReportOut(
            date=current,
            sessions_started=0,
            total_hours=0.0
        )
        current += timedelta(days=1)

    for session in sessions:
        day = session.started_at.date()
        if day in report:
            report[day].sessions_started += 1
            if session.total_minutes is not None:
                report[day].total_hours += session.total_minutes / 60

    for entry in report.values():
        entry.total_hours = round(entry.total_hours, 2)

    return [report[d] for d in sorted(report.keys())]

@router.get("/report-by-worker", response_model=list[WorkerReportOut])
async def report_by_worker(
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager)
):
    from_date, to_date = default_range(from_date, to_date)

    workers_result = await db.execute(
        select(User).where(User.role.in_(["pyme", "vehicular", "convenio"]))
    )
    workers = workers_result.scalars().all()

    report: dict[int, WorkerReportOut] = {
        worker.id: WorkerReportOut(
            worker_id=worker.id,
            worker_name=worker.name,
            total_sessions=0,
            total_hours=0.0
        )
        for worker in workers
    }

    sessions_result = await db.execute(
        select(Session).where(
            Session.started_at >= datetime.combine(from_date, time.min),
            Session.started_at <= datetime.combine(to_date, time.max),
            Session.status != "active"
        )
    )
    for session in sessions_result.scalars().all():
        entry = report.get(session.user_id)
        if entry is None:
            continue
        entry.total_sessions += 1
        if session.total_minutes is not None:
            entry.total_hours += session.total_minutes / 60

    for entry in report.values():
        entry.total_hours = round(entry.total_hours, 2)

    return sorted(report.values(), key=lambda e: e.worker_name)