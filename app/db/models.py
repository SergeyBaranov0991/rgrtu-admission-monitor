from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    max_user_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    exam_score: Mapped[int] = mapped_column(Integer, default=195)
    achievements: Mapped[int] = mapped_column(Integer, default=0)
    search_profile: Mapped[str] = mapped_column(String(16), default="score")
    entrant_code: Mapped[str | None] = mapped_column(String(32))
    category_scope: Mapped[str] = mapped_column(String(16), default="general")
    pending_action: Mapped[str | None] = mapped_column(String(32))
    notifications_enabled: Mapped[int] = mapped_column(Integer, default=1)
    paid_enabled: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Snapshot(Base):
    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_code: Mapped[str] = mapped_column(String(16), index=True)
    funding_type: Mapped[str] = mapped_column(String(16), index=True)
    source_hash: Mapped[str | None] = mapped_column(String(128))
    zone: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[float] = mapped_column(Float)
    payload_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class ProcessedUpdate(Base):
    __tablename__ = "processed_updates"
    __table_args__ = (UniqueConstraint("update_id", name="uq_processed_update_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    update_id: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
