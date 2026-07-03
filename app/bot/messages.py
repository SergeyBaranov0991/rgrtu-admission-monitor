from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.admission.estimator import AdmissionEstimate
from app.admission.zones import ZONE_LABELS
from app.rgrtu.base import SourceStatus


def render_status(estimates: list[AdmissionEstimate], *, score: int, tz: str = "Europe/Moscow") -> str:
    now = datetime.now(ZoneInfo(tz)).strftime("%d.%m.%Y %H:%M")
    lines = [
        f"РГРТУ - статус на {now} МСК",
        f"Конкурсный балл: {score}",
        "",
    ]
    for estimate in estimates:
        lines.extend(render_estimate_block(estimate))
        lines.append("")
    lines.append("Это оценка, а не гарантия зачисления.")
    return "\n".join(lines).strip()


def render_estimate_block(estimate: AdmissionEstimate) -> list[str]:
    funding = "бюджет" if estimate.funding_type == "budget" else "платное"
    position = estimate.raw_position
    position_text = _interval(position) if position else "нет данных"
    forecast = _interval(estimate.forecast_passing_score) if estimate.forecast_passing_score else "нет данных"
    confidence = _confidence_label(estimate.confidence)
    preliminary = " (предварительно)" if estimate.preliminary else ""
    applications_count = _applications_count_label(estimate)

    return [
        f"{estimate.program_code} {estimate.program_name} - {funding}",
        f"Источник: {_source_label(estimate)}",
        f"Мест: {estimate.places}",
        f"Подано заявлений: {applications_count}",
        f"Оценочная позиция: {position_text}",
        f"Текущий проходной: {estimate.current_passing_score or 'нет данных'}",
        f"Прогноз проходного: {forecast}{preliminary}",
        f"Статус: {ZONE_LABELS[estimate.zone]}",
        f"Достоверность: {confidence}",
    ]


def render_programs() -> str:
    from app.config import PROGRAMS

    lines = ["Отслеживаемые направления:"]
    for program in PROGRAMS:
        lines.append(
            f"{program.code} - {program.name}; бюджет: {program.general_places}, платное: {program.paid_places}"
        )
    return "\n".join(lines)


def render_help() -> str:
    return "\n".join(
        [
            "Нажмите кнопку «Актуальный статус», чтобы получить свежую оценку по направлениям.",
            "",
            "Текстовая команда /status тоже работает.",
        ]
    )


def _interval(value: tuple[int, int] | None) -> str:
    if value is None:
        return "нет данных"
    if value[0] == value[1]:
        return str(value[0])
    return f"{value[0]}-{value[1]}"


def _confidence_label(value: float) -> str:
    if value >= 0.75:
        return "высокая"
    if value >= 0.5:
        return "средняя"
    return "низкая"


def _applications_count_label(estimate: AdmissionEstimate) -> str:
    if estimate.source_status != SourceStatus.OK:
        return "не определено"
    label = str(estimate.rows_count)
    scored = estimate.scored_rows_count
    if scored is not None and scored != estimate.rows_count:
        label = f"{label} (с баллами: {scored})"
    return label


def _source_label(estimate: AdmissionEstimate) -> str:
    if estimate.source_status == SourceStatus.OK:
        if estimate.rows_count == 0:
            return "данные получены, заявлений нет"
        return "данные получены"
    if estimate.source_status == SourceStatus.SCHEMA_CHANGED:
        return "ошибка разбора данных РГРТУ"
    return "ошибка получения данных РГРТУ"
