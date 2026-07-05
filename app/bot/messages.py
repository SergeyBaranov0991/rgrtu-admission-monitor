from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.admission.estimator import AdmissionEstimate
from app.admission.zones import ZONE_LABELS
from app.rgrtu.base import SourceStatus


def render_status(
    estimates: list[AdmissionEstimate],
    *,
    score: int,
    entrant_code: str | None = None,
    category_scope: str = "general",
    relative: bool = False,
    debug: bool = False,
    tz: str = "Europe/Moscow",
) -> str:
    now = datetime.now(ZoneInfo(tz)).strftime("%d.%m.%Y %H:%M")
    title = "РГРТУ - относительный статус" if relative else "РГРТУ - статус вне приоритетов"
    lines = [
        f"{title} на {now} МСК",
        _profile_label(score=score, entrant_code=entrant_code),
    ]
    if debug:
        lines.extend(
            [
                f"Режим категорий: {_category_scope_label(category_scope)}",
                f"Режим расчета: {_calculation_mode_label(relative)}",
                "",
            ]
        )
    else:
        lines.extend([f"Категории: {_category_scope_label(category_scope)}", ""])
    for estimate in estimates:
        lines.extend(render_estimate_block(estimate, debug=debug))
        lines.append("")
    warning = None if debug else _compact_warning(estimates)
    if warning:
        lines.append(warning)
    lines.append("Это оценка, а не гарантия зачисления.")
    return "\n".join(lines).strip()


def render_estimate_block(estimate: AdmissionEstimate, *, debug: bool = False) -> list[str]:
    if not debug:
        return _render_compact_estimate_block(estimate)

    funding = _funding_label(estimate)
    position = estimate.raw_position
    position_text = _interval(position) if position else "нет данных"
    if estimate.relative_excluded_by:
        position_text = "не учитывается"
    forecast = _forecast_label(estimate)
    confidence = _confidence_label(estimate.confidence)
    preliminary = " (предварительно)" if estimate.preliminary else ""
    applications_count = _applications_count_label(estimate)
    passing_score = _value_or_no_data(estimate.current_passing_score)
    position_label = (
        "Относительная позиция"
        if estimate.ranking_mode == "relative"
        else "Оценочная позиция"
    )

    lines = [
        f"{estimate.program_code} {estimate.program_name} - {funding}",
        f"Источник: {_source_label(estimate)}",
        f"Мест: {estimate.places}",
        f"Подано заявлений: {applications_count}",
    ]
    if estimate.relative_rows_count is not None:
        lines.append(f"Учитывается после приоритетов: {estimate.relative_rows_count}")
    if estimate.target_entrant_code:
        lines.append(f"Код в списке: {_target_code_label(estimate)}")
    if estimate.target_priority is not None:
        lines.append(f"Приоритет в списке: {estimate.target_priority}")
    lines.extend(
        [
            f"{position_label}: {position_text}",
            f"Текущий проходной: {passing_score}",
        ]
    )
    if estimate.published_score_floor is not None:
        lines.append(
            f"Нижняя граница по опубликованным баллам: {estimate.published_score_floor}"
        )
    note = _calculation_note(estimate)
    if note:
        lines.append(note)
    relative_note = _relative_note(estimate)
    if relative_note:
        lines.append(relative_note)
    lines.extend(
        [
            f"Прогноз проходного: {forecast}{preliminary}",
            f"Статус: {ZONE_LABELS[estimate.zone]}",
            f"Достоверность: {confidence}",
        ]
    )
    return lines


def _render_compact_estimate_block(estimate: AdmissionEstimate) -> list[str]:
    funding = _funding_label(estimate)
    position = estimate.raw_position
    position_text = _interval(position) if position else "нет данных"
    if estimate.relative_excluded_by:
        position_text = "не учитывается"

    lines = [f"{estimate.program_code} {estimate.program_name} - {funding}"]
    if estimate.source_status != SourceStatus.OK or estimate.rows_count == 0:
        lines.append(f"Источник: {_source_label(estimate)}")

    if estimate.source_status == SourceStatus.OK:
        lines.append(f"Мест: {estimate.places}; заявлений: {estimate.rows_count}")
    else:
        lines.extend([f"Мест: {estimate.places}", "Заявлений: не определено"])

    if estimate.target_entrant_code:
        lines.append(f"Код: {_compact_target_code_label(estimate)}")
    if estimate.target_priority is not None:
        lines.append(f"Приоритет: {estimate.target_priority}")

    lines.extend(
        [
            f"Позиция: {position_text}",
            f"Проходной сейчас: {_value_or_no_data(estimate.current_passing_score)}",
        ]
    )
    if estimate.relative_excluded_by:
        lines.append(f"Причина: проходит выше по приоритету в {estimate.relative_excluded_by}")
    lines.extend(
        [
            f"Статус: {ZONE_LABELS[estimate.zone]}",
            f"Достоверность: {_confidence_label(estimate.confidence)}",
        ]
    )
    return lines


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
            "Нажмите «Актуальный статус вне приоритетов» для обычной оценки по опубликованному списку.",
            "Нажмите «Актуальный относительный статус» для оценки с учетом более высоких приоритетов.",
            "",
            "/setup запускает настройку текущего чата. Если указан код заявки, первый статус найдет до 5 направлений по всем очным спискам РГРТУ и сохранит их в профиль. Если указан только балл, бот попросит направления в формате 01.03.02;1.",
            "",
            "По умолчанию статус компактный: места, заявления, позиция, проходной, статус и достоверность.",
            "/debug включает или выключает подробный режим. В подробном режиме показываются источник, строки с баллами, расчет, фильтрация и прогноз.",
            "",
            "Относительный статус исключает заявку из направления, если тот же код уверенно проходит на более высоком приоритете в выбранном режиме категорий. Спорные равные баллы на границе мест остаются в расчете.",
            "Если опубликованных баллов меньше, чем мест, проходной может быть не рассчитан, а достоверность будет минимальной.",
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


def _value_or_no_data(value: int | None) -> str:
    return str(value) if value is not None else "нет данных"


def _forecast_label(estimate: AdmissionEstimate) -> str:
    if estimate.forecast_passing_score:
        return _interval(estimate.forecast_passing_score)
    if estimate.draft_forecast_score:
        return f"черновой {_interval(estimate.draft_forecast_score)}"
    return "нет данных"


def _profile_label(*, score: int, entrant_code: str | None) -> str:
    if entrant_code:
        return f"Код из сервиса приема: {entrant_code}"
    return f"Конкурсный балл: {score}"


def _category_scope_label(value: str) -> str:
    return "все категории" if value == "all" else "только общий конкурс"


def _calculation_mode_label(relative: bool) -> str:
    return "с учетом приоритетов" if relative else "вне приоритетов"


def _funding_label(estimate: AdmissionEstimate) -> str:
    funding = "платное" if estimate.funding_type == "paid" else "бюджет"
    basis = estimate.admission_basis.strip()
    if not basis or basis == "general":
        return funding
    if basis.casefold() in {"общий конкурс", "по договору"}:
        return funding
    return f"{funding}, {basis}"


def _confidence_label(value: float) -> str:
    if value >= 0.75:
        return "высокая"
    if value >= 0.5:
        return "средняя"
    if value < 0.25:
        return "минимальная"
    return "низкая"


def _applications_count_label(estimate: AdmissionEstimate) -> str:
    if estimate.source_status != SourceStatus.OK:
        return "не определено"
    label = str(estimate.rows_count)
    scored = estimate.scored_rows_count
    if scored is not None and scored != estimate.rows_count:
        scored_label = (
            "с баллами после фильтрации"
            if estimate.ranking_mode == "relative"
            else "с баллами"
        )
        label = f"{label} ({scored_label}: {scored})"
    return label


def _target_code_label(estimate: AdmissionEstimate) -> str:
    if estimate.target_found is True:
        return f"{estimate.target_entrant_code} найден"
    if estimate.target_found is False:
        return f"{estimate.target_entrant_code} не найден"
    return f"{estimate.target_entrant_code} не проверен"


def _compact_target_code_label(estimate: AdmissionEstimate) -> str:
    if estimate.target_found is True:
        return "найден"
    if estimate.target_found is False:
        return "не найден"
    return "не проверен"


def _calculation_note(estimate: AdmissionEstimate) -> str | None:
    if estimate.source_status != SourceStatus.OK:
        return None
    scored = estimate.scored_rows_count
    if scored is None or scored == estimate.rows_count:
        return None
    if scored < estimate.places:
        return (
            f"Расчет: позиция, нижняя граница и черновой прогноз по {scored} строкам с баллами; "
            f"для обычного проходного нужно минимум {estimate.places}."
        )
    return f"Расчет: по {scored} строкам с баллами."


def _relative_note(estimate: AdmissionEstimate) -> str | None:
    if estimate.ranking_mode != "relative":
        return None
    if estimate.relative_excluded_by:
        return f"Относительный расчет: заявка проходит выше по приоритету в {estimate.relative_excluded_by}."
    return "Относительный расчет: исключены заявки, проходящие по более высокому приоритету в выбранном режиме категорий."


def _compact_warning(estimates: list[AdmissionEstimate]) -> str | None:
    if any(estimate.source_status != SourceStatus.OK for estimate in estimates):
        return "Есть ошибки получения данных. Включите /debug, чтобы увидеть детали источника."
    if any(
        estimate.source_status == SourceStatus.OK
        and estimate.scored_rows_count is not None
        and estimate.scored_rows_count < estimate.places
        for estimate in estimates
    ):
        return "Часть списков содержит мало опубликованных баллов, поэтому оценка предварительная."
    return None


def _source_label(estimate: AdmissionEstimate) -> str:
    if estimate.source_status == SourceStatus.OK:
        if estimate.rows_count == 0:
            return "данные получены, заявлений нет"
        return "данные получены"
    if estimate.source_status == SourceStatus.SCHEMA_CHANGED:
        return "ошибка разбора данных РГРТУ"
    return "ошибка получения данных РГРТУ"
