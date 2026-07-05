from __future__ import annotations

from dataclasses import dataclass
import re

from app.admission.estimator import AdmissionEstimate
from app.bot.keyboards import (
    is_all_categories_request,
    is_general_only_request,
    is_relative_status_request,
    is_search_by_code_request,
    is_search_by_score_request,
    is_status_request,
)
from app.bot.messages import render_help, render_programs, render_status
from app.bot.profile import (
    ProfileParseError,
    ProgramPriority,
    decode_program_priorities,
    encode_program_priorities,
    format_program_priorities,
    parse_program_priorities,
    program_priority_map,
)
from app.bot.user_settings import UserSettingsStore
from app.config import Settings, get_program
from app.db.models import UserSettings
from app.jobs.check_lists import estimate_from_live
from app.rgrtu.base import SourceStatus

SETUP_PROGRAMS_ACTION = "setup_programs"
SETUP_IDENTITY_ACTION = "setup_identity"


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
        or is_relative_status_request(text)
        or is_search_by_score_request(text)
        or is_search_by_code_request(text)
        or is_general_only_request(text)
        or is_all_categories_request(text)
    )

    if user_settings is not None and user_settings.pending_action and not text.startswith("/") and not is_control_text:
        return _handle_pending_input(user_settings, text, store)

    if is_status_request(text):
        return await _render_current_status(context.settings, user_settings, store, relative=False)

    if is_relative_status_request(text):
        return await _render_current_status(context.settings, user_settings, store, relative=True)

    if is_search_by_score_request(text):
        if user_settings is None:
            return "Не удалось сохранить профиль: не определен пользователь."
        user_settings.search_profile = "score"
        user_settings.pending_action = "score"
        store.save(user_settings)
        return (
            f"Профиль поиска: по баллу.\n"
            f"Текущий балл: {_user_total_score(user_settings)}.\n\n"
            "Отправьте новый балл числом, например 195, или нажмите кнопку статуса."
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
        if _needs_onboarding(user_settings):
            return _start_onboarding(user_settings, store)
        return "Бот РГРТУ запущен.\n\n" + render_help() + "\n\n" + _render_settings(user_settings)
    if command == "/help":
        return render_help()
    if command in {"/setup", "/onboarding"}:
        return _start_onboarding(user_settings, store)
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
        return _set_debug(user_settings, arg, store)
    return "Команда не распознана.\n\n" + render_help()


def _handle_pending_input(settings: UserSettings, text: str, store: UserSettingsStore) -> str:
    if settings.pending_action == SETUP_PROGRAMS_ACTION:
        return _set_onboarding_programs(settings, text, store)
    if settings.pending_action == SETUP_IDENTITY_ACTION:
        return _set_onboarding_identity(settings, text, store)
    if settings.pending_action == "score":
        return _set_score(settings, text, store)
    if settings.pending_action == "entrant_code":
        return _set_entrant_code(settings, text, store)
    settings.pending_action = None
    store.save(settings)
    return "Ожидаемое действие сброшено."


def _needs_onboarding(settings: UserSettings | None) -> bool:
    if settings is None:
        return False
    if settings.search_profile == "code":
        return not bool(settings.entrant_code)
    return not bool(decode_program_priorities(settings.program_priorities_json))


def _start_onboarding(settings: UserSettings | None, store: UserSettingsStore) -> str:
    if settings is None:
        return "Не удалось сохранить профиль: не определен пользователь."
    settings.pending_action = SETUP_IDENTITY_ACTION
    store.save(settings)
    return (
        "Настроим профиль для этого чата.\n\n"
        "Шаг 1. Отправьте код из сервиса приема или ориентировочный конкурсный балл.\n"
        "Если число состоит из 3 цифр, считаю его баллом. Если длиннее - кодом заявки.\n\n"
        "При наличии кода заявки направления и приоритеты будут взяты из списков РГРТУ."
    )


def _set_onboarding_programs(settings: UserSettings, text: str, store: UserSettingsStore) -> str:
    try:
        priorities = parse_program_priorities(text)
    except ProfileParseError as exc:
        return (
            f"{exc}\n\n"
            "Пример корректного ввода:\n"
            "01.03.02;1\n"
            "09.03.03;2"
        )

    settings.program_priorities_json = encode_program_priorities(priorities)
    settings.pending_action = None
    store.save(settings)
    return _onboarding_complete_message(settings)


def _set_onboarding_identity(settings: UserSettings, text: str, store: UserSettingsStore) -> str:
    value = _single_number_from_text(text)
    if value is None:
        return "Отправьте одно число: 195 для балла или 1158236 для кода заявки."

    if len(value) == 3:
        score = int(value)
        if not 0 <= score <= 310:
            return "Балл должен быть в диапазоне 0-310."
        settings.exam_score = score
        settings.achievements = 0
        settings.search_profile = "score"
        settings.pending_action = SETUP_PROGRAMS_ACTION
        store.save(settings)
        return (
            f"Балл {score} сохранен.\n\n"
            "Шаг 2. Так как кода заявки нет, отправьте направления и их приоритеты, каждое с новой строки:\n"
            "01.03.02;1\n"
            "09.03.03;2\n\n"
            "Приоритеты не должны повторяться. Список направлений можно посмотреть командой /programs."
        )

    if len(value) > 3:
        settings.entrant_code = value
        settings.program_priorities_json = None
        settings.search_profile = "code"
        settings.pending_action = None
        store.save(settings)
        return _onboarding_complete_message(settings)

    return "Слишком короткое число. Укажите 3-значный балл или более длинный код заявки."


def _single_number_from_text(text: str) -> str | None:
    numbers = re.findall(r"\d+", text)
    if len(numbers) != 1:
        return None
    return numbers[0]


def _onboarding_complete_message(settings: UserSettings) -> str:
    note = (
        "Первый запрос статуса найдет до 5 направлений по этому коду и сохранит их в профиль."
        if settings.search_profile == "code"
        else "Для режима по баллу используется заданный вручную порядок направлений."
    )
    return (
        "Профиль сохранен для этого чата.\n\n"
        f"{note}\n\n"
        f"{_render_settings(settings)}\n\n"
        "Теперь нажмите кнопку актуального статуса или отправьте /relative."
    )


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
    settings.program_priorities_json = None
    settings.search_profile = "code"
    settings.pending_action = None
    store.save(settings)
    return (
        f"Код из сервиса приема {code} сохранен. "
        "Следующий запрос статуса найдет до 5 направлений по этому коду и сохранит их в профиль."
    )


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


def _set_debug(settings: UserSettings | None, value: str, store: UserSettingsStore) -> str:
    if settings is None:
        return "Не удалось сохранить debug-режим: не определен пользователь."
    normalized = value.strip().casefold()
    if normalized in {"on", "1", "true", "yes", "вкл", "включить", "включен"}:
        enabled = True
    elif normalized in {"off", "0", "false", "no", "выкл", "выключить", "выключен"}:
        enabled = False
    else:
        enabled = not _debug_enabled(settings)

    settings.debug_enabled = 1 if enabled else 0
    settings.pending_action = None
    store.save(settings)
    if enabled:
        return "Подробный режим включен. Следующий статус покажет источник, расчет, фильтрацию и прогноз."
    return "Подробный режим выключен. Следующий статус будет компактным."


async def _render_current_status(
    settings: Settings,
    user_settings: UserSettings | None,
    store: UserSettingsStore,
    *,
    relative: bool,
) -> str:
    score = _score_for_status(settings, user_settings)
    scope = _category_scope(user_settings)
    entrant_code = _entrant_code_for_status(user_settings)
    if user_settings and user_settings.search_profile == "code" and not entrant_code:
        return "Профиль поиска: по коду. Сначала задайте код кнопкой «Искать по коду» или командой /code 1158236."
    search_all_full_time = bool(user_settings and user_settings.search_profile == "code" and entrant_code)
    estimates = await estimate_from_live(
        score,
        settings,
        category_scope=scope,
        entrant_code=entrant_code,
        relative=relative,
        search_all_full_time=search_all_full_time,
    )
    if user_settings is not None and entrant_code and user_settings.search_profile == "code":
        _save_discovered_code_profile(user_settings, estimates, store)
    estimates = _apply_program_profile(estimates, user_settings, category_scope=scope)
    if search_all_full_time and not estimates:
        return f"Код {entrant_code} не найден в загруженных очных списках РГРТУ."
    return render_status(
        estimates,
        score=score,
        entrant_code=entrant_code,
        category_scope=scope,
        relative=relative,
        debug=_debug_enabled(user_settings),
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
    return render_status(
        estimates,
        score=score,
        entrant_code=entrant_code,
        category_scope=scope,
        debug=_debug_enabled(user_settings),
        tz=settings.timezone,
    )


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


def _debug_enabled(settings: UserSettings | None) -> bool:
    return bool(settings and settings.debug_enabled)


def _apply_program_profile(
    estimates: list[AdmissionEstimate],
    settings: UserSettings | None,
    *,
    category_scope: str = "general",
) -> list[AdmissionEstimate]:
    if settings is None:
        return estimates
    if settings.search_profile == "code":
        return _sort_code_profile_estimates(
            estimates,
            program_priorities=program_priority_map(settings.program_priorities_json),
            category_scope=category_scope,
        )
    if settings.search_profile != "score":
        return estimates
    priorities = program_priority_map(settings.program_priorities_json)
    if not priorities:
        return estimates
    funding_order = {"budget": 0, "paid": 1}
    selected = [estimate for estimate in estimates if estimate.program_code in priorities]
    return sorted(
        selected,
        key=lambda estimate: (
            priorities[estimate.program_code],
            funding_order.get(estimate.funding_type, 9),
            estimate.program_code,
        ),
    )


def _save_discovered_code_profile(
    settings: UserSettings,
    estimates: list[AdmissionEstimate],
    store: UserSettingsStore,
) -> None:
    if decode_program_priorities(settings.program_priorities_json):
        return
    discovered = _discover_code_program_priorities(estimates)
    if not discovered:
        return
    settings.program_priorities_json = encode_program_priorities(discovered)
    store.save(settings)


def _discover_code_program_priorities(estimates: list[AdmissionEstimate]) -> list[ProgramPriority]:
    discovered: dict[str, ProgramPriority] = {}
    for estimate in estimates:
        if estimate.target_found is not True or estimate.target_priority is None:
            continue
        current = discovered.get(estimate.program_code)
        if current is not None and current.priority <= estimate.target_priority:
            continue
        discovered[estimate.program_code] = ProgramPriority(
            code=estimate.program_code,
            priority=estimate.target_priority,
            name=estimate.program_name,
        )
    return sorted(discovered.values(), key=lambda item: (item.priority, item.code))[:5]


def _sort_code_profile_estimates(
    estimates: list[AdmissionEstimate],
    *,
    program_priorities: dict[str, int],
    category_scope: str,
) -> list[AdmissionEstimate]:
    if program_priorities:
        selected = [
            estimate
            for estimate in estimates
            if estimate.program_code in program_priorities
            and estimate.target_found is True
            and _matches_category_scope(estimate, category_scope)
        ]
    else:
        selected = [
            estimate
            for estimate in estimates
            if estimate.target_found is True and _matches_category_scope(estimate, category_scope)
        ]
    if not selected:
        if any(estimate.source_status != SourceStatus.OK for estimate in estimates):
            return estimates
        return []
    funding_order = {"budget": 0, "paid": 1}
    return sorted(
        selected,
        key=lambda estimate: (
            program_priorities.get(
                estimate.program_code,
                estimate.target_priority if estimate.target_priority is not None else 10**9,
            ),
            funding_order.get(estimate.funding_type, 9),
            estimate.program_code,
        ),
    )


def _matches_category_scope(estimate: AdmissionEstimate, category_scope: str) -> bool:
    if category_scope == "all":
        return True
    basis = estimate.admission_basis.strip().casefold()
    return estimate.funding_type == "budget" and basis in {"", "general", "общий конкурс"}


def _render_settings(settings: UserSettings | None) -> str:
    if settings is None:
        return "Настройки не сохранены: пользователь не определен."
    profile = "код из сервиса приема" if settings.search_profile == "code" else "балл"
    code = settings.entrant_code or "не задан"
    debug = "включен" if _debug_enabled(settings) else "выключен"
    program_priorities = (
        format_program_priorities(settings.program_priorities_json)
        if settings.program_priorities_json
        else "будут найдены при первом запросе статуса по коду заявки"
        if settings.search_profile == "code" and settings.entrant_code
        else format_program_priorities(settings.program_priorities_json)
    )
    return "\n".join(
        [
            "Текущие настройки:",
            "Направления по приоритетам:",
            program_priorities,
            f"Профиль поиска: {profile}",
            f"Балл: {_user_total_score(settings)}",
            f"Код из сервиса приема: {code}",
            f"Режим категорий: {_category_scope_label(_category_scope(settings))}",
            f"Подробный режим: {debug}",
            "",
            "Кнопки ниже позволяют изменить профиль и режим.",
        ]
    )


def _category_scope_label(value: str) -> str:
    return "все категории" if value == "all" else "только общий конкурс"
