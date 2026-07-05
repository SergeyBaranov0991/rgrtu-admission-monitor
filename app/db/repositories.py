from __future__ import annotations

from sqlalchemy import inspect, select
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base, UserSettings, utcnow


def build_session_factory(database_url: str) -> sessionmaker[Session]:
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
    )
    if database_url.startswith("sqlite"):
        with engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA journal_mode=WAL")
    Base.metadata.create_all(engine)
    if database_url.startswith("sqlite"):
        _ensure_sqlite_user_settings_columns(engine)
    return sessionmaker(engine, expire_on_commit=False)


def get_or_create_user_settings(
    session: Session,
    *,
    user_id: str,
    default_score: int,
    default_achievements: int,
) -> UserSettings:
    settings = session.scalar(select(UserSettings).where(UserSettings.max_user_id == user_id))
    if settings is not None:
        return settings
    settings = UserSettings(
        max_user_id=user_id,
        exam_score=default_score,
        achievements=default_achievements,
        search_profile="score",
        category_scope="general",
        debug_enabled=0,
    )
    session.add(settings)
    session.commit()
    session.refresh(settings)
    return settings


def touch_user_settings(settings: UserSettings) -> None:
    settings.updated_at = utcnow()


def _ensure_sqlite_user_settings_columns(engine) -> None:
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("user_settings")}
    migrations = {
        "search_profile": "ALTER TABLE user_settings ADD COLUMN search_profile VARCHAR(16) DEFAULT 'score'",
        "entrant_code": "ALTER TABLE user_settings ADD COLUMN entrant_code VARCHAR(32)",
        "program_priorities_json": "ALTER TABLE user_settings ADD COLUMN program_priorities_json TEXT",
        "category_scope": "ALTER TABLE user_settings ADD COLUMN category_scope VARCHAR(16) DEFAULT 'general'",
        "debug_enabled": "ALTER TABLE user_settings ADD COLUMN debug_enabled INTEGER DEFAULT 0",
        "pending_action": "ALTER TABLE user_settings ADD COLUMN pending_action VARCHAR(32)",
    }
    with engine.begin() as connection:
        for column, ddl in migrations.items():
            if column not in columns:
                connection.exec_driver_sql(ddl)
