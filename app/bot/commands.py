from __future__ import annotations

from dataclasses import dataclass

from app.bot.keyboards import is_status_request
from app.bot.messages import render_help, render_programs, render_status
from app.config import Settings, get_program
from app.jobs.check_lists import estimate_from_live


@dataclass
class CommandContext:
    user_id: str | None
    text: str
    settings: Settings


async def handle_command(context: CommandContext) -> str:
    text = context.text.strip()
    if is_status_request(text):
        estimates = await estimate_from_live(context.settings.total_default_score, context.settings)
        return render_status(estimates, score=context.settings.total_default_score)

    command, _, arg = text.partition(" ")

    if command in {"/start", "start"}:
        return "Бот РГРТУ запущен.\n\n" + render_help()
    if command == "/help":
        return render_help()
    if command == "/programs":
        return render_programs()
    if command == "/score":
        return _validate_score(arg)
    if command == "/achievements":
        return _validate_achievements(arg)
    if command == "/program":
        return await _render_program(arg, context.settings)
    if command == "/history":
        return "История событий будет доступна после подключения БД snapshots."
    if command == "/debug":
        return "Приложение: OK\nРГРТУ: discovery adapter\nMAX: client configured"
    return "Команда не распознана.\n\n" + render_help()


def _validate_score(value: str) -> str:
    try:
        score = int(value)
    except ValueError:
        return "Укажите балл числом: /score 195"
    if not 0 <= score <= 310:
        return "Балл должен быть в диапазоне 0-310."
    return f"Балл {score} принят. Сохранение в БД будет подключено следующим этапом."


def _validate_achievements(value: str) -> str:
    try:
        achievements = int(value)
    except ValueError:
        return "Укажите индивидуальные достижения числом: /achievements 5"
    if not 0 <= achievements <= 10:
        return "Индивидуальные достижения должны быть в диапазоне 0-10."
    return f"Индивидуальные достижения {achievements} приняты."


async def _render_program(code: str, settings: Settings) -> str:
    program = get_program(code.strip())
    if program is None:
        return "Направление не найдено. Используйте /programs."
    estimates = [
        estimate
        for estimate in await estimate_from_live(settings.total_default_score, settings)
        if estimate.program_code == program.code
    ]
    return render_status(estimates, score=settings.total_default_score)
