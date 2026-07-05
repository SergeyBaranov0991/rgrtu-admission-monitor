from sqlalchemy import select

from app.admission.estimator import AdmissionEstimate
from app.admission.zones import AdmissionZone
from app.bot import commands
from app.bot.commands import CommandContext, handle_command
from app.bot.keyboards import (
    ALL_CATEGORIES_BUTTON_TEXT,
    RELATIVE_STATUS_BUTTON_TEXT,
    SEARCH_BY_CODE_BUTTON_TEXT,
)
from app.config import Settings
from app.db.models import UserSettings
from app.db.repositories import build_session_factory


def _settings(tmp_path) -> Settings:
    db_path = tmp_path / "settings.db"
    return Settings(database_url=f"sqlite:///{db_path.as_posix()}")


def _estimate(
    code: str,
    *,
    target_found: bool | None = None,
    target_priority: int | None = None,
) -> AdmissionEstimate:
    return AdmissionEstimate(
        program_code=code,
        program_name=f"Направление {code}",
        funding_type="budget",
        places=10,
        target_score=195,
        raw_position=None,
        effective_position=None,
        current_passing_score=None,
        forecast_passing_score=None,
        zone=AdmissionZone.INSUFFICIENT_DATA,
        confidence=0.1,
        preliminary=True,
        rows_count=1,
        target_entrant_code="1158236" if target_found is not None else None,
        target_found=target_found,
        target_priority=target_priority,
    )


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


async def test_relative_status_button_uses_relative_estimate(tmp_path, monkeypatch) -> None:
    settings = _settings(tmp_path)
    calls: list[dict] = []

    async def fake_estimate_from_live(*args, **kwargs) -> list:
        calls.append({"args": args, "kwargs": kwargs})
        return []

    monkeypatch.setattr(commands, "estimate_from_live", fake_estimate_from_live)

    reply = await handle_command(
        CommandContext(user_id="tg:123", text=RELATIVE_STATUS_BUTTON_TEXT, settings=settings)
    )

    assert "Режим расчета: с учетом приоритетов" not in reply
    assert calls[0]["kwargs"]["relative"] is True


async def test_debug_command_toggles_detailed_status(tmp_path, monkeypatch) -> None:
    settings = _settings(tmp_path)
    calls: list[dict] = []

    async def fake_estimate_from_live(*args, **kwargs) -> list:
        calls.append({"args": args, "kwargs": kwargs})
        return []

    monkeypatch.setattr(commands, "estimate_from_live", fake_estimate_from_live)

    enabled = await handle_command(CommandContext(user_id="tg:123", text="/debug on", settings=settings))
    detailed = await handle_command(
        CommandContext(user_id="tg:123", text=RELATIVE_STATUS_BUTTON_TEXT, settings=settings)
    )
    disabled = await handle_command(CommandContext(user_id="tg:123", text="/debug off", settings=settings))
    compact = await handle_command(
        CommandContext(user_id="tg:123", text=RELATIVE_STATUS_BUTTON_TEXT, settings=settings)
    )

    assert "Подробный режим включен" in enabled
    assert "Режим расчета: с учетом приоритетов" in detailed
    assert "Подробный режим выключен" in disabled
    assert "Режим расчета: с учетом приоритетов" not in compact
    assert calls[0]["kwargs"]["relative"] is True


async def test_onboarding_with_entrant_code_does_not_ask_priorities(tmp_path) -> None:
    settings = _settings(tmp_path)

    prompt = await handle_command(CommandContext(user_id="tg:123", text="/setup", settings=settings))
    reply = await handle_command(CommandContext(user_id="tg:123", text="1158236", settings=settings))

    assert "код из сервиса приема" in prompt
    assert "Профиль сохранен" in reply
    assert "Приоритеты будут определяться" in reply
    assert "Шаг 2" not in reply
    session_factory = build_session_factory(settings.database_url)
    with session_factory() as session:
        saved = session.scalar(select(UserSettings).where(UserSettings.max_user_id == "tg:123"))
        assert saved is not None
        assert saved.search_profile == "code"
        assert saved.entrant_code == "1158236"
        assert saved.program_priorities_json is None
        assert saved.pending_action is None


async def test_onboarding_with_score_requires_program_priorities(tmp_path) -> None:
    settings = _settings(tmp_path)

    await handle_command(CommandContext(user_id="tg:123", text="/setup", settings=settings))
    score_reply = await handle_command(CommandContext(user_id="tg:123", text="195", settings=settings))
    complete = await handle_command(
        CommandContext(
            user_id="tg:123",
            text="09.03.03;2\n01.03.02;1",
            settings=settings,
        )
    )

    assert "Так как кода заявки нет" in score_reply
    assert "Профиль сохранен" in complete
    assert "01.03.02" in complete
    assert "09.03.03" in complete
    session_factory = build_session_factory(settings.database_url)
    with session_factory() as session:
        saved = session.scalar(select(UserSettings).where(UserSettings.max_user_id == "tg:123"))
        assert saved is not None
        assert saved.search_profile == "score"
        assert saved.exam_score == 195
        assert saved.program_priorities_json is not None
        assert '"code": "01.03.02"' in saved.program_priorities_json
        assert saved.pending_action is None


def test_program_profile_applies_only_to_score_profile() -> None:
    estimates = [
        _estimate("09.03.03"),
        _estimate("01.03.02"),
        _estimate("09.03.02"),
    ]
    score_settings = UserSettings(
        max_user_id="tg:score",
        search_profile="score",
        program_priorities_json='[{"code": "09.03.03", "priority": 2}, {"code": "01.03.02", "priority": 1}]',
    )
    code_settings = UserSettings(
        max_user_id="tg:code",
        search_profile="code",
        entrant_code="1158236",
        program_priorities_json=score_settings.program_priorities_json,
    )
    code_estimates = [
        _estimate("09.03.03", target_found=True, target_priority=2),
        _estimate("01.03.02", target_found=True, target_priority=1),
        _estimate("09.03.02", target_found=False),
    ]

    score_result = commands._apply_program_profile(estimates, score_settings)
    code_result = commands._apply_program_profile(code_estimates, code_settings)

    assert [estimate.program_code for estimate in score_result] == ["01.03.02", "09.03.03"]
    assert [estimate.program_code for estimate in code_result] == ["01.03.02", "09.03.03"]
