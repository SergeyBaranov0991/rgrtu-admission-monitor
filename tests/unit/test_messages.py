from app.admission.estimator import AdmissionEstimate
from app.admission.zones import AdmissionZone
from app.bot.messages import render_estimate_block
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

    assert "Подано заявлений: 21" in render_estimate_block(estimate)


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
        zone=AdmissionZone.INSUFFICIENT_DATA,
        confidence=0.2,
        preliminary=True,
        rows_count=99,
        scored_rows_count=7,
    )

    block = render_estimate_block(estimate)

    assert "Подано заявлений: 99 (с баллами: 7)" in block
    assert "Оценочная позиция: 5" in block
    assert "Оценочная позиция: 2" not in block


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

    block = render_estimate_block(estimate)

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
    assert "Подано заявлений: 0" in block


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
    assert "Подано заявлений: не определено" in block
    assert "Подано заявлений: 0" not in block


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
