from __future__ import annotations

from functools import lru_cache

from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.db.models import UserSettings
from app.db.repositories import build_session_factory, get_or_create_user_settings, touch_user_settings


class UserSettingsStore:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._session_factory = _session_factory(settings.database_url)

    def load(self, user_id: str | None) -> UserSettings | None:
        if not user_id:
            return None
        with self._session_factory() as session:
            settings = get_or_create_user_settings(
                session,
                user_id=user_id,
                default_score=self._settings.default_exam_score,
                default_achievements=self._settings.individual_achievements,
            )
            session.expunge(settings)
            return settings

    def save(self, settings: UserSettings) -> None:
        with self._session_factory() as session:
            merged = session.merge(settings)
            touch_user_settings(merged)
            session.commit()


@lru_cache
def _session_factory(database_url: str) -> sessionmaker:
    return build_session_factory(database_url)
