from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import Session, LocationLog
from app.dependencies import get_current_user
from app.models import User
from app.schemas import SessionStart, SessionOut, SessionEndOut, LocationLogRequest
from datetime import datetime, timezone
from app.models import SystemEventLog
from app.schemas import SystemEventCreate, SystemEventOut
from app.models import HeartbeatLog
from app.schemas import HeartbeatCreate, HeartbeatOut
router = APIRouter()

SEVERE_EVENT_TYPES = {
    "mock_location_detected",
    "permission_revoked",
    "gps_unavailable",
    "foreground_service_closed",
    "sync_failed",
}
NO_INTERNET_THRESHOLD_MINUTES = 60

@router.post("/", response_model=SessionOut)
async def start_session(
    body: SessionStart,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Abortar cualquier sesión activa previa del mismo worker
    prev_result = await db.execute(
        select(Session).where(
            Session.user_id == current_user.id,
            Session.status == "active"
        )
    )
    prev_sessions = prev_result.scalars().all()
    now = datetime.now(timezone.utc)
    for prev in prev_sessions:
        prev.status = "aborted"
        prev.ended_at = now
        prev.total_minutes = int((now - prev.started_at).total_seconds() / 60)

    new_session = Session(
        user_id=current_user.id,
        place_id=body.place_id,
        started_at=now,
        status="active"
    )
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    return new_session

@router.patch("/{session_id}/end", response_model=SessionEndOut)
async def end_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == current_user.id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    events_result = await db.execute(
        select(SystemEventLog).where(SystemEventLog.session_id == session_id)
    )
    events = events_result.scalars().all()

    has_observations = any(e.event_type in SEVERE_EVENT_TYPES for e in events)
    if not has_observations:
        has_observations = any(
            e.event_type == "no_internet"
            and e.duration_minutes is not None
            and e.duration_minutes >= NO_INTERNET_THRESHOLD_MINUTES
            for e in events
        )

    now = datetime.now(timezone.utc)
    session.ended_at = now
    session.total_minutes = int((now - session.started_at).total_seconds() / 60)
    session.status = "completed_with_observations" if has_observations else "completed"

    await db.commit()
    await db.refresh(session)
    return session

@router.post("/location-logs")
async def log_location(
    body: LocationLogRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user)
):
    log = LocationLog(
        session_id=body.session_id,
        lat=body.lat,
        lng=body.lng,
        accuracy_m=body.accuracy_m,
        recorded_at=body.recorded_at,
        uploaded_at=datetime.now(timezone.utc)
    )
    db.add(log)
    await db.commit()
    return {"ok": True}

@router.post("/events", response_model=SystemEventOut)
async def log_system_event(
    body: SystemEventCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user)
):
    event = SystemEventLog(
        session_id=body.session_id,
        event_type=body.event_type,
        detail=body.detail,
        duration_minutes=body.duration_minutes,
        occurred_at=body.occurred_at,
        synced=True
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event

@router.post("/events", response_model=SystemEventOut)
async def log_system_event(
    body: SystemEventCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user)
):
    event = SystemEventLog(
        session_id=body.session_id,
        event_type=body.event_type,
        detail=body.detail,
        duration_minutes=body.duration_minutes,
        occurred_at=body.occurred_at,
        synced=True
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event




@router.post("/heartbeat", response_model=HeartbeatOut)
async def send_heartbeat(
    body: HeartbeatCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user)
):
    heartbeat = HeartbeatLog(
        session_id=body.session_id,
        sent_at=body.sent_at,
        responded=True
    )
    db.add(heartbeat)
    await db.commit()
    await db.refresh(heartbeat)
    return heartbeat
