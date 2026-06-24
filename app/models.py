from sqlalchemy import (
    Column, Integer, String, Boolean, Float,
    Text, ForeignKey, CheckConstraint
)
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime, timezone


def now_utc():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(
        String(20),
        nullable=False,
        info={"check": "role IN ('worker', 'manager')"}
    )
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=now_utc)

    sessions = relationship("Session", back_populates="user")
    places_created = relationship("Place", back_populates="creator")
    checkins = relationship("PlaceCheckin", back_populates="user")


class Place(Base):
    __tablename__ = "places"

    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    address = Column(String(255))
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=now_utc)

    creator = relationship("User", back_populates="places_created")
    sessions = relationship("Session", back_populates="place")
    checkins = relationship("PlaceCheckin", back_populates="place")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    place_id = Column(Integer, ForeignKey("places.id", ondelete="RESTRICT"), nullable=False)
    started_at = Column(TIMESTAMP(timezone=True), nullable=False, default=now_utc)
    ended_at = Column(TIMESTAMP(timezone=True))
    total_km = Column(Float)
    total_minutes = Column(Integer)
    status = Column(
        String(50),
        nullable=False,
        default="active",
        info={"check": "status IN ('active', 'completed', 'completed_with_observations')"}
    )

    user = relationship("User", back_populates="sessions")
    place = relationship("Place", back_populates="sessions")
    location_logs = relationship("LocationLog", back_populates="session")
    heartbeat_logs = relationship("HeartbeatLog", back_populates="session")
    system_event_logs = relationship("SystemEventLog", back_populates="session")
    checkins = relationship("PlaceCheckin", back_populates="session")


class LocationLog(Base):
    __tablename__ = "location_logs"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    accuracy_m = Column(Float)
    recorded_at = Column(TIMESTAMP(timezone=True), nullable=False)
    uploaded_at = Column(TIMESTAMP(timezone=True), nullable=False, default=now_utc)
    synced = Column(Boolean, nullable=False, default=True)

    session = relationship("Session", back_populates="location_logs")


class HeartbeatLog(Base):
    __tablename__ = "heartbeat_logs"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    sent_at = Column(TIMESTAMP(timezone=True), nullable=False)
    responded = Column(Boolean, nullable=False, default=False)

    session = relationship("Session", back_populates="heartbeat_logs")


class SystemEventLog(Base):
    __tablename__ = "system_event_logs"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(50), nullable=False)
    detail = Column(Text, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    occurred_at = Column(TIMESTAMP(timezone=True), nullable=False)
    synced = Column(Boolean, nullable=False, default=True)

    session = relationship("Session", back_populates="system_event_logs")  # ← esto faltaba

class PlaceCheckin(Base):
    __tablename__ = "place_checkins"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    place_id = Column(Integer, ForeignKey("places.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    distance_m = Column(Float)
    accuracy_m = Column(Float)
    notes = Column(Text)
    mocked_location = Column(Boolean, nullable=False, default=False)
    checked_in_at = Column(TIMESTAMP(timezone=True), nullable=False, default=now_utc)

    session = relationship("Session", back_populates="checkins")
    place = relationship("Place", back_populates="checkins")
    user = relationship("User", back_populates="checkins")
