from pydantic import BaseModel
from datetime import datetime
from typing import Optional


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

class PlaceOut(BaseModel):
    id: int
    name: str
    address: Optional[str]
    lat: float
    lng: float

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