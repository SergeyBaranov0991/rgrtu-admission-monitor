from app.admission.estimator import AdmissionEstimate
from app.admission.zones import AdmissionZone
from app.bot.messages import render_estimate_block


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
