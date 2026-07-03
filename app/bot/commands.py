from __future__ import annotations

from dataclasses import dataclass

from app.bot.keyboards import (
    is_all_categories_request,
    is_general_only_request,
    is_search_by_code_request,
    is_search_by_score_request,
    is_status_request,
)
from app.bot.messages import render_help, render_programs, render_status
from app.bot.user_settings import UserSettingsStore
from app.config import Settings, get_program
from app.db.models import UserSettings
from app.jobs.check_lists import estimate_from_live


@dataclass
class CommandContext:
    user_id: str | None
    text: str
    settings: Settings


async def handle_command(context: CommandContext) -> str:
    text = context.text.strip()
    store = UserSettingsStore(context.settings)
    user_settings = store.load(context.user_id)
    is_control_text = (
        is_status_request(text)
        or is_search_by_score_request(text)
        or is_search_by_code_request(text)
        or is_general_only_request(text)
        or is_all_categories_request(text)
    )

    if user_settings is not None and user_settings.pending_action and not text.startswith("/") and not is_control_text:
        return _handle_pending_input(user_settings, text, store)

    if is_status_request(text):
        return await _render_current_status(context.settings, user_settings)

    if is_search_by_score_request(text):
        if user_settings is None:
            return "Не удалось сохранить профиль: не определен пользователь."
        user_settings.search_profile = "score"
        user_settings.pending_action = "score"
        store.save(user_settings)
        return (
            f"Профиль поиска: по баллу.\n"
            f"Текущий балл: {_user_total_score(user_settings)}.\n\n"
            "Отправьте новый балл числом, например 195, или нажмите «Актуальный статус»."
        )

    if is_search_by_code_request(text):
        if user_settings is None:
            return "Не удалось сохранить профиль: не определен пользователь."
        user_settings.search_profile = "code"
        user_settings.pending_action = "entrant_code"
        store.save(user_settings)
        current = f"\nТекущий код: {user_settings.entrant_code}" if user_settings.entrant_code else ""
        return (
            f"Профиль поиска: по коду из сервиса приема.{current}\n\n"
            "Отправьте код числом, например 1158236."
        )

    if is_general_only_request(text):
        if user_settings is None:
            return "Не удалось сохранить режим: не определен пользователь."
        user_settings.category_scope = "general"
        user_settings.pending_action = None
        store.save(user_settings)
        return "Режим категорий: только общий конкурс."

    if is_all_categories_request(text):
        if user_settings is None:
            return "Не удалось сохранить режим: не определен пользователь."
        user_settings.category_scope = "all"
        user_settings.pending_action = None
        store.save(user_settings)
        return "Режим категорий: все категории."

    command, _, arg = text.partition(" ")

    if command in {"/start", "start"}:
        return "Бот РГРТУ запущен.\n\n" + render_help() + "\n\n" + _render_settings(user_settings)
    if command == "/help":
        return render_help()
    if command == "/settings":
        return _render_settings(user_settings)
    if command == "/programs":
        return render_programs()
    if command == "/score":
        return _set_score(user_settings, arg, store)
    if command == "/code":
        return _set_entrant_code(user_settings, arg, store)
    if command == "/scope":
        return _set_scope(user_settings, arg, store)
    if command == "/achievements":
        return _set_achievements(user_settings, arg, store)
    if command == "/program":
        return await _render_program(arg, context.settings, user_settings)
    if command == "/history":
        return "История событий будет доступна после подключения БД snapshots."
    if command == "/debug":
        return "Приложение: OK\nРГРТУ: discovery adapter\nMAX: client configured"
    return "Команда не распознана.\n\n" + render_help()


def _handle_pending_input(settings: UserSettings, text: str, store: UserSettingsStore) -> str:
    if settings.pending_action == "score":
        return _set_score(settings, text, store)
    if settings.pending_action == "entrant_code":
        return _set_entrant_code(settings, text, store)
    settings.pending_action = None
    store.save(settings)
    return "Ожидаемое действие сброшено."


def _set_score(settings: UserSettings | None, value: str, store: UserSettingsStore) -> str:
    if settings is None:
        return "Не удалось сохранить балл: не определен пользователь."
    try:
        score = int(value)
    except ValueError:
        return "Укажите балл числом: /score 195"
    if not 0 <= score <= 310:
        return "Балл должен быть в диапазоне 0-310."
    settings.exam_score = score
    settings.search_profile = "score"
    settings.pending_action = None
    store.save(settings)
    return f"Балл {score} сохранен. Текущий конкурсный балл: {_user_total_score(settings)}."


def _set_achievements(settings: UserSettings | None, value: str, store: UserSettingsStore) -> str:
    if settings is None:
        return "Не удалось сохранить индивидуальные достижения: не определен пользователь."
    try:
        achievements = int(value)
    except ValueError:
        return "Укажите индивидуальные достижения числом: /achievements 5"
    if not 0 <= achievements <= 10:
        return "Индивидуальные достижения должны быть в диапазоне 0-10."
    settings.achievements = achievements
    settings.pending_action = None
    store.save(settings)
    return f"Индивидуальные достижения {achievements} сохранены."


def _set_entrant_code(settings: UserSettings | None, value: str, store: UserSettingsStore) -> str:
    if settings is None:
        return "Не удалось сохранить код: не определен пользователь."
    code = value.strip()
    if not code.isdigit():
        return "Укажите код из сервиса приема числом: /code 1158236"
    settings.entrant_code = code
    settings.search_profile = "code"
    settings.pending_action = None
    store.save(settings)
    return f"Код из сервиса приема {code} сохранен."


def _set_scope(settings: UserSettings | None, value: str, store: UserSettingsStore) -> str:
    if settings is None:
        return "Не удалось сохранить режим: не определен пользователь."
    normalized = value.strip().casefold()
    if normalized in {"general", "общий", "только общий конкурс"}:
        settings.category_scope = "general"
    elif normalized in {"all", "все", "все категории"}:
        settings.category_scope = "all"
    else:
        return "Укажите режим: /scope general или /scope all"
    settings.pending_action = None
    store.save(settings)
    return f"Режим категорий: {_category_scope_label(settings.category_scope)}."


async def _render_current_status(settings: Settings, user_settings: UserSettings | None) -> str:
    score = _score_for_status(settings, user_settings)
    scope = _category_scope(user_settings)
    entrant_code = _entrant_code_for_status(user_settings)
    if user_settings and user_settings.search_profile == "code" and not entrant_code:
        return "Профиль поиска: по коду. Сначала задайте код кнопкой «Искать по коду» или командой /code 1158236."
    estimates = await estimate_from_live(
        score,
        settings,
        category_scope=scope,
        entrant_code=entrant_code,
    )
    return render_status(
        estimates,
        score=score,
        entrant_code=entrant_code,
        category_scope=scope,
        tz=settings.timezone,
    )


async def _render_program(code: str, settings: Settings, user_settings: UserSettings | None) -> str:
    program = get_program(code.strip())
    if program is None:
        return "Направление не найдено. Используйте /programs."
    score = _score_for_status(settings, user_settings)
    scope = _category_scope(user_settings)
    entrant_code = _entrant_code_for_status(user_settings)
    estimates = [
        estimate
        for estimate in await estimate_from_live(
            score,
            settings,
            category_scope=scope,
            entrant_code=entrant_code,
        )
        if estimate.program_code == program.code
    ]
    return render_status(estimates, score=score, entrant_code=entrant_code, category_scope=scope, tz=settings.timezone)


def _score_for_status(settings: Settings, user_settings: UserSettings | None) -> int:
    if user_settings is None:
        return settings.total_default_score
    return _user_total_score(user_settings)


def _user_total_score(settings: UserSettings) -> int:
    return int(settings.exam_score or 0) + int(settings.achievements or 0)


def _category_scope(settings: UserSettings | None) -> str:
    if settings is None:
        return "general"
    return settings.category_scope if settings.category_scope in {"general", "all"} else "general"


def _entrant_code_for_status(settings: UserSettings | None) -> str | None:
    if settings is None or settings.search_profile != "code":
        return None
    return settings.entrant_code


def _render_settings(settings: UserSettings | None) -> str:
    if settings is None:
        return "Настройки не сохранены: пользователь не определен."
    profile = "код из сервиса приема" if settings.search_profile == "code" else "балл"
    code = settings.entrant_code or "не задан"
    return "\n".join(
        [
            "Текущие настройки:",
            f"Профиль поиска: {profile}",
            f"Балл: {_user_total_score(settings)}",
            f"Код из сервиса приема: {code}",
            f"Режим категорий: {_category_scope_label(_category_scope(settings))}",
            "",
            "Кнопки ниже позволяют изменить профиль и режим.",
        ]
    )


def _category_scope_label(value: str) -> str:
    return "все категории" if value == "all" else "только общий конкурс"
