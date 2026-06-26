from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from datetime import date, datetime

# ─── Auth ───────────────────────────────────────────
class LoginRequest(BaseModel):
    email: str
    password: str

class UserOut(BaseModel):
    id: int
    name: str
    role: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserOut


# ─── Places ─────────────────────────────────────────
class PlaceCreate(BaseModel):
    name: str
    address: Optional[str] = None
    lat: float
    lng: float
    # El worker pyme nunca manda role_assign, lo manda solo el manager
    role_assign: Optional[str] = None

class PlaceOut(BaseModel):
    id: int
    name: str
    address: Optional[str]
    lat: float
    lng: float
    active: bool
    created_by: Optional[int]
    role_assign: Optional[str]
    requested_by_role: Optional[str] = None

    class Config:
        from_attributes = True

class CheckinRequest(BaseModel):
    session_id: int
    place_id: int
    lat: float
    lng: float
    accuracy_m: Optional[float] = None
    notes: Optional[str] = None

class CheckinOut(BaseModel):
    id: int
    session_id: int
    place_id: int
    checked_in_at: datetime

    class Config:
        from_attributes = True


# ─── Sessions ───────────────────────────────────────
class SessionStart(BaseModel):
    place_id: int

class SessionOut(BaseModel):
    id: int
    user_id: int
    place_id: int
    started_at: datetime
    status: str

    class Config:
        from_attributes = True

class SessionEndOut(BaseModel):
    id: int
    status: str
    ended_at: datetime
    total_minutes: int

    class Config:
        from_attributes = True


# ─── Location logs ──────────────────────────────────
class LocationLogRequest(BaseModel):
    session_id: int
    lat: float
    lng: float
    accuracy_m: Optional[float] = None
    recorded_at: datetime

# ─── Manager: Workers ───────────────────────────────
class WorkerCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str = "worker"  # permite crear otro manager si hace falta

class WorkerOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class WorkerUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    active: Optional[bool] = None
    password: Optional[str] = None  # opcional, para resetear contraseña

    # ─── System events ──────────────────────────────────
class SystemEventCreate(BaseModel):
    session_id: int
    event_type: str
    detail: Optional[str] = None
    duration_minutes: Optional[int] = None
    occurred_at: datetime

class SystemEventOut(BaseModel):
    id: int
    session_id: int
    event_type: str
    detail: Optional[str]
    duration_minutes: Optional[int]
    occurred_at: datetime

    class Config:
        from_attributes = True

# ─── Manager: Sessions ──────────────────────────────
class ActiveSessionOut(BaseModel):
    id: int
    worker_name: str
    place_name: str
    started_at: datetime
    status: str

class LastLocationOut(BaseModel):
    lat: float
    lng: float
    recorded_at: datetime

class VisitedPlaceOut(BaseModel):
    place_id: int
    place_name: str
    checked_in_at: datetime

class SessionDetailOut(BaseModel):
    id: int
    worker_id: int
    worker_name: str
    place_id: int
    place_name: str
    started_at: datetime
    ended_at: Optional[datetime]
    total_minutes: Optional[int]
    status: str
    visited_places: list[VisitedPlaceOut]
    last_location: Optional[LastLocationOut]

class TrackPointOut(BaseModel):
    lat: float
    lng: float
    accuracy_m: Optional[float]
    recorded_at: datetime

class SessionHistoryOut(BaseModel):
    id: int
    worker_id: int
    worker_name: str
    place_name: str
    started_at: datetime
    ended_at: Optional[datetime]
    total_minutes: Optional[int]
    status: str

# ─── Manager: Places ────────────────────────────────
class PlaceManagerOut(BaseModel):
    id: int
    name: str
    address: Optional[str]
    lat: float
    lng: float
    active: bool
    created_by: Optional[int]
    role_assign: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class PlaceUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    active: Optional[bool] = None

class PlaceVisitOut(BaseModel):
    checkin_id: int
    worker_id: int
    worker_name: str
    session_id: int
    checked_in_at: datetime
    notes: Optional[str]

# ─── Manager: Dashboard ─────────────────────────────
class DayReportOut(BaseModel):
    date: date
    sessions_started: int
    total_hours: float

class WorkerReportOut(BaseModel):
    worker_id: int
    worker_name: str
    total_sessions: int
    total_hours: float

# ─── Heartbeat ──────────────────────────────────────
class HeartbeatCreate(BaseModel):
    session_id: int
    sent_at: datetime

class HeartbeatOut(BaseModel):
    id: int
    session_id: int
    sent_at: datetime
    responded: bool

    class Config:
        from_attributes = True

class ActiveSessionOut(BaseModel):
    id: int
    worker_name: str
    place_name: str
    started_at: datetime
    status: str
    is_online: bool
    last_seen_minutes_ago: int
