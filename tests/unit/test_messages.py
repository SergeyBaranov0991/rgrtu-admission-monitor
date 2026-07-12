from app.admission.estimator import AdmissionEstimate
from app.admission.zones import AdmissionZone
from app.bot.messages import render_estimate_block, render_status
from app.rgrtu.base import SourceStatus


def test_render_estimate_block_includes_application_count() -> None:
    estimate = AdmissionEstimate(
        program_code="09.03.02",
        program_name="Информационные системы и технологии",
        funding_type="budget",
        places=19,
        target_score=195,
        raw_position=(16, 18),
        effective_position=(16, 18),
        current_passing_score=193,
        forecast_passing_score=(186, 200),
        zone=AdmissionZone.PASSING,
        confidence=0.6,
        preliminary=True,
        rows_count=21,
    )

    assert "Мест: 19; заявлений: 21" in render_estimate_block(estimate)


def test_render_estimate_block_uses_raw_position_and_shows_scored_count() -> None:
    estimate = AdmissionEstimate(
        program_code="09.03.03",
        program_name="Прикладная информатика",
        funding_type="budget",
        places=20,
        target_score=195,
        raw_position=(5, 5),
        effective_position=(2, 2),
        current_passing_score=None,
        forecast_passing_score=None,
        published_score_floor=186,
        draft_forecast_score=(171, 201),
        zone=AdmissionZone.INSUFFICIENT_DATA,
        confidence=0.2,
        preliminary=True,
        rows_count=99,
        scored_rows_count=7,
    )

    block = render_estimate_block(estimate, debug=True)

    assert "Подано заявлений: 99 (с баллами: 7)" in block
    assert "Оценочная позиция: 5" in block
    assert "Нижняя граница по опубликованным баллам: 186" in block
    assert "Расчет: позиция, нижняя граница и черновой прогноз по 7 строкам с баллами; для обычного проходного нужно минимум 20." in block
    assert "Прогноз проходного: черновой 171-201 (предварительно)" in block
    assert "Достоверность: минимальная" in block
    assert "Оценочная позиция: 2" not in block


def test_render_estimate_block_debug_shows_absent_decision_data() -> None:
    estimate = AdmissionEstimate(
        program_code="09.03.03",
        program_name="Прикладная информатика",
        funding_type="budget",
        places=20,
        target_score=195,
        raw_position=(5, 5),
        effective_position=(5, 5),
        current_passing_score=193,
        forecast_passing_score=(186, 200),
        zone=AdmissionZone.PASSING,
        confidence=0.6,
        preliminary=True,
        rows_count=21,
        scored_rows_count=21,
        decision_rows_count=0,
        consent_rows_count=0,
        original_rows_count=0,
        higher_priority_status_rows_count=0,
    )

    block = render_estimate_block(estimate, debug=True)

    assert "Согласия/ВПП/ОВП: нет данных в этом списке." in block


def test_render_estimate_block_debug_shows_available_decision_data() -> None:
    estimate = AdmissionEstimate(
        program_code="09.03.03",
        program_name="Прикладная информатика",
        funding_type="budget",
        places=20,
        target_score=195,
        raw_position=(5, 5),
        effective_position=(5, 5),
        current_passing_score=193,
        forecast_passing_score=(186, 200),
        zone=AdmissionZone.PASSING,
        confidence=0.6,
        preliminary=True,
        rows_count=21,
        scored_rows_count=21,
        decision_rows_count=7,
        consent_rows_count=2,
        original_rows_count=3,
        higher_priority_status_rows_count=4,
    )

    block = render_estimate_block(estimate, debug=True)

    assert "Согласия/ВПП/ОВП: строк с данными: 7; согласия: 2; оригиналы: 3; ВПП/ОВП: 4." in block


def test_render_estimate_block_compact_hides_decision_data_note() -> None:
    estimate = AdmissionEstimate(
        program_code="09.03.03",
        program_name="Прикладная информатика",
        funding_type="budget",
        places=20,
        target_score=195,
        raw_position=(5, 5),
        effective_position=(5, 5),
        current_passing_score=193,
        forecast_passing_score=(186, 200),
        zone=AdmissionZone.PASSING,
        confidence=0.6,
        preliminary=True,
        rows_count=21,
        scored_rows_count=21,
        decision_rows_count=0,
    )

    block = render_estimate_block(estimate)

    assert not any("ВПП" in line for line in block)


def test_render_estimate_block_shows_category_and_code_status() -> None:
    estimate = AdmissionEstimate(
        program_code="01.03.02",
        program_name="Прикладная математика и информатика",
        funding_type="budget",
        admission_basis="Отдельная квота",
        places=2,
        target_score=195,
        raw_position=(1, 1),
        effective_position=None,
        current_passing_score=195,
        forecast_passing_score=None,
        zone=AdmissionZone.PASSING,
        confidence=0.6,
        preliminary=True,
        rows_count=3,
        scored_rows_count=3,
        target_entrant_code="1158236",
        target_found=True,
    )

    block = render_estimate_block(estimate, debug=True)

    assert block[0] == "01.03.02 Прикладная математика и информатика - бюджет, Отдельная квота"
    assert "Код в списке: 1158236 найден" in block


def test_render_estimate_block_distinguishes_real_zero_applications() -> None:
    estimate = AdmissionEstimate(
        program_code="09.03.02",
        program_name="Информационные системы и технологии",
        funding_type="budget",
        places=19,
        target_score=195,
        raw_position=None,
        effective_position=None,
        current_passing_score=None,
        forecast_passing_score=None,
        zone=AdmissionZone.INSUFFICIENT_DATA,
        confidence=0.2,
        preliminary=True,
        source_status=SourceStatus.OK,
        rows_count=0,
    )

    block = render_estimate_block(estimate)

    assert "Источник: данные получены, заявлений нет" in block
    assert "Мест: 19; заявлений: 0" in block


def test_render_estimate_block_does_not_show_zero_for_source_error() -> None:
    estimate = AdmissionEstimate(
        program_code="09.03.02",
        program_name="Информационные системы и технологии",
        funding_type="budget",
        places=19,
        target_score=195,
        raw_position=None,
        effective_position=None,
        current_passing_score=None,
        forecast_passing_score=None,
        zone=AdmissionZone.SOURCE_UNAVAILABLE,
        confidence=0.0,
        preliminary=True,
        source_status=SourceStatus.UNAVAILABLE,
        rows_count=0,
    )

    block = render_estimate_block(estimate)

    assert "Источник: ошибка получения данных РГРТУ" in block
    assert "Заявлений: не определено" in block
    assert "заявлений: 0" not in block


def test_render_estimate_block_shows_parse_error() -> None:
    estimate = AdmissionEstimate(
        program_code="09.03.02",
        program_name="Информационные системы и технологии",
        funding_type="budget",
        places=19,
        target_score=195,
        raw_position=None,
        effective_position=None,
        current_passing_score=None,
        forecast_passing_score=None,
        zone=AdmissionZone.SOURCE_UNAVAILABLE,
        confidence=0.0,
        preliminary=True,
        source_status=SourceStatus.SCHEMA_CHANGED,
        rows_count=0,
    )

    assert "Источник: ошибка разбора данных РГРТУ" in render_estimate_block(estimate)


def test_render_relative_status_and_exclusion_note() -> None:
    estimate = AdmissionEstimate(
        program_code="09.03.03",
        program_name="Прикладная информатика",
        funding_type="budget",
        places=20,
        target_score=195,
        raw_position=None,
        effective_position=None,
        current_passing_score=183,
        forecast_passing_score=(176, 190),
        zone=AdmissionZone.HIGHER_PRIORITY,
        confidence=0.6,
        preliminary=True,
        rows_count=99,
        scored_rows_count=20,
        target_entrant_code="1158236",
        target_found=True,
        target_priority=2,
        ranking_mode="relative",
        relative_rows_count=12,
        relative_excluded_by="01.03.02 Прикладная математика и информатика - бюджет",
    )

    status = render_status(
        [estimate],
        score=195,
        entrant_code="1158236",
        category_scope="general",
        relative=True,
    )

    assert "РГРТУ - относительный статус" in status
    assert "Режим расчета: с учетом приоритетов" not in status
    assert "Мест: 20; заявлений: 99" in status
    assert "Код: найден" in status
    assert "Код: 1158236 найден" not in status
    assert "Учитывается после приоритетов: 12" not in status
    assert "Приоритет 2: 09.03.03 Прикладная информатика - бюджет" in status
    assert "Позиция: не учитывается" in status
    assert "Причина: проходит выше по приоритету в 01.03.02" in status
    assert "Статус: проходит выше по приоритету" in status
    assert "Относительный расчет:" not in status


def test_render_relative_status_debug_keeps_details() -> None:
    estimate = AdmissionEstimate(
        program_code="09.03.03",
        program_name="Прикладная информатика",
        funding_type="budget",
        places=20,
        target_score=195,
        raw_position=None,
        effective_position=None,
        current_passing_score=183,
        forecast_passing_score=(176, 190),
        zone=AdmissionZone.HIGHER_PRIORITY,
        confidence=0.6,
        preliminary=True,
        rows_count=99,
        scored_rows_count=20,
        target_entrant_code="1158236",
        target_found=True,
        target_priority=2,
        ranking_mode="relative",
        relative_rows_count=12,
        relative_excluded_by="01.03.02 Прикладная математика и информатика - бюджет",
    )

    status = render_status(
        [estimate],
        score=195,
        entrant_code="1158236",
        category_scope="general",
        relative=True,
        debug=True,
    )

    assert "Режим расчета: с учетом приоритетов" in status
    assert "Подано заявлений: 99 (с баллами после фильтрации: 20)" in status
    assert "Учитывается после приоритетов: 12" in status
    assert "Приоритет в списке: 2" in status
    assert "Относительная позиция: не учитывается" in status
    assert "Относительный расчет:" in status


def test_render_status_sorts_blocks_by_target_priority() -> None:
    estimates = [
        AdmissionEstimate(
            program_code="09.03.03",
            program_name="Прикладная информатика",
            funding_type="budget",
            places=20,
            target_score=195,
            raw_position=(3, 3),
            effective_position=None,
            current_passing_score=None,
            forecast_passing_score=None,
            zone=AdmissionZone.INSUFFICIENT_DATA,
            confidence=0.1,
            preliminary=True,
            rows_count=1,
            target_priority=3,
        ),
        AdmissionEstimate(
            program_code="09.03.02",
            program_name="Информационные системы и технологии",
            funding_type="budget",
            places=19,
            target_score=195,
            raw_position=(1, 1),
            effective_position=None,
            current_passing_score=None,
            forecast_passing_score=None,
            zone=AdmissionZone.PASSING,
            confidence=0.1,
            preliminary=True,
            rows_count=1,
            target_priority=1,
        ),
    ]

    status = render_status(estimates, score=195)

    assert status.index("Приоритет 1: 09.03.02") < status.index("Приоритет 3: 09.03.03")
