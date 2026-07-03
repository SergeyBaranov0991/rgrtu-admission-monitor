from sqlalchemy import select

from app.bot.commands import CommandContext, handle_command
from app.bot.keyboards import ALL_CATEGORIES_BUTTON_TEXT, SEARCH_BY_CODE_BUTTON_TEXT
from app.config import Settings
from app.db.models import UserSettings
from app.db.repositories import build_session_factory


def _settings(tmp_path) -> Settings:
    db_path = tmp_path / "settings.db"
    return Settings(database_url=f"sqlite:///{db_path.as_posix()}")


async def test_score_command_saves_user_profile(tmp_path) -> None:
    settings = _settings(tmp_path)

    reply = await handle_command(CommandContext(user_id="tg:123", text="/score 201", settings=settings))

    assert "Балл 201 сохранен" in reply
    session_factory = build_session_factory(settings.database_url)
    with session_factory() as session:
        saved = session.scalar(select(UserSettings).where(UserSettings.max_user_id == "tg:123"))
        assert saved is not None
        assert saved.exam_score == 201
        assert saved.search_profile == "score"


async def test_code_button_waits_for_code_and_saves_it(tmp_path) -> None:
    settings = _settings(tmp_path)

    prompt = await handle_command(
        CommandContext(user_id="tg:123", text=SEARCH_BY_CODE_BUTTON_TEXT, settings=settings)
    )
    reply = await handle_command(CommandContext(user_id="tg:123", text="1158236", settings=settings))

    assert "Отправьте код" in prompt
    assert "1158236 сохранен" in reply
    session_factory = build_session_factory(settings.database_url)
    with session_factory() as session:
        saved = session.scalar(select(UserSettings).where(UserSettings.max_user_id == "tg:123"))
        assert saved is not None
        assert saved.search_profile == "code"
        assert saved.entrant_code == "1158236"
        assert saved.pending_action is None


async def test_all_categories_button_saves_scope(tmp_path) -> None:
    settings = _settings(tmp_path)

    reply = await handle_command(
        CommandContext(user_id="tg:123", text=ALL_CATEGORIES_BUTTON_TEXT, settings=settings)
    )

    assert "все категории" in reply
    session_factory = build_session_factory(settings.database_url)
    with session_factory() as session:
        saved = session.scalar(select(UserSettings).where(UserSettings.max_user_id == "tg:123"))
        assert saved is not None
        assert saved.category_scope == "all"
