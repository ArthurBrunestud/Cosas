from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import Session, LocationLog
from app.dependencies import get_current_user
from app.models import User
from app.schemas import SessionStart, SessionOut, SessionEndOut, LocationLogRequest
from datetime import datetime, timezone

router = APIRouter()

@router.post("/", response_model=SessionOut)
async def start_session(
    body: SessionStart,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session = Session(
        user_id=current_user.id,
        place_id=body.place_id,
        status="active"
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session

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

    now = datetime.now(timezone.utc)
    session.ended_at = now
    session.total_minutes = int((now - session.started_at).total_seconds() / 60)
    session.status = "completed"
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