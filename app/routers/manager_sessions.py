from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import Session, User, Place, PlaceCheckin, LocationLog
from app.dependencies import get_current_manager
from app.schemas import (
    ActiveSessionOut, SessionDetailOut, VisitedPlaceOut,
    LastLocationOut, TrackPointOut
)
from app.models import SystemEventLog
from app.schemas import SystemEventCreate, SystemEventOut
from datetime import datetime, timezone
from app.models import HeartbeatLog

router = APIRouter()
HEARTBEAT_INTERVAL_MINUTES = 10
HEARTBEAT_DOWN_THRESHOLD_MINUTES = HEARTBEAT_INTERVAL_MINUTES * 3


@router.get("/", response_model=list[ActiveSessionOut])
async def list_active_sessions(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager)
):
    result = await db.execute(
        select(Session, User.name, Place.name)
        .join(User, Session.user_id == User.id)
        .join(Place, Session.place_id == Place.id)
        .where(Session.status == "active")
    )
    rows = result.all()

    active_sessions = []
    now = datetime.now(timezone.utc)

    for session, worker_name, place_name in rows:
        last_hb_result = await db.execute(
            select(HeartbeatLog)
            .where(HeartbeatLog.session_id == session.id)
            .order_by(HeartbeatLog.sent_at.desc())
            .limit(1)
        )
        last_hb = last_hb_result.scalar_one_or_none()

        if last_hb is None:
            minutes_since_last_seen = int((now - session.started_at).total_seconds() / 60)
        else:
            minutes_since_last_seen = int((now - last_hb.sent_at).total_seconds() / 60)

        is_online = minutes_since_last_seen < HEARTBEAT_DOWN_THRESHOLD_MINUTES

        active_sessions.append(
            ActiveSessionOut(
                id=session.id,
                worker_name=worker_name,
                place_name=place_name,
                started_at=session.started_at,
                status=session.status,
                is_online=is_online,
                last_seen_minutes_ago=minutes_since_last_seen
            )
        )

    return active_sessions

@router.get("/{session_id}", response_model=SessionDetailOut)
async def get_session_detail(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager)
):
    result = await db.execute(
        select(Session, User.name, Place.name)
        .join(User, Session.user_id == User.id)
        .join(Place, Session.place_id == Place.id)
        .where(Session.id == session_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    session, worker_name, place_name = row

    checkins_result = await db.execute(
        select(PlaceCheckin, Place.name)
        .join(Place, PlaceCheckin.place_id == Place.id)
        .where(PlaceCheckin.session_id == session_id)
        .order_by(PlaceCheckin.checked_in_at)
    )
    visited_places = [
        VisitedPlaceOut(
            place_id=checkin.place_id,
            place_name=p_name,
            checked_in_at=checkin.checked_in_at
        )
        for checkin, p_name in checkins_result.all()
    ]

    last_log_result = await db.execute(
        select(LocationLog)
        .where(LocationLog.session_id == session_id)
        .order_by(LocationLog.recorded_at.desc())
        .limit(1)
    )
    last_log = last_log_result.scalar_one_or_none()
    last_location = (
        LastLocationOut(lat=last_log.lat, lng=last_log.lng, recorded_at=last_log.recorded_at)
        if last_log else None
    )

    return SessionDetailOut(
        id=session.id,
        worker_id=session.user_id,
        worker_name=worker_name,
        place_id=session.place_id,
        place_name=place_name,
        started_at=session.started_at,
        ended_at=session.ended_at,
        total_minutes=session.total_minutes,
        status=session.status,
        visited_places=visited_places,
        last_location=last_location
    )


@router.get("/{session_id}/track", response_model=list[TrackPointOut])
async def get_session_track(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager)
):
    result = await db.execute(
        select(LocationLog)
        .where(LocationLog.session_id == session_id)
        .order_by(LocationLog.recorded_at)
    )
    return result.scalars().all()

@router.get("/{session_id}/events", response_model=list[SystemEventOut])
async def get_session_events(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_manager)
):
    result = await db.execute(
        select(SystemEventLog)
        .where(SystemEventLog.session_id == session_id)
        .order_by(SystemEventLog.occurred_at)
    )
    return result.scalars().all()