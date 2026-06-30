from datetime import date

from app.admission.estimator import estimate_competition
from app.admission.zones import AdmissionZone
from app.rgrtu.base import SourceStatus
from app.rgrtu.parser import parse_fixture_file


def test_estimator_marks_borderline_interval() -> None:
    competition = parse_fixture_file("tests/fixtures/rgrtu/competition_list_full.json")[0]

    estimate = estimate_competition(competition, 195, today=date(2026, 7, 29))

    assert estimate.zone == AdmissionZone.PASSING
    assert estimate.raw_position == (16, 18)
    assert estimate.current_passing_score == 193


def test_estimator_marks_preliminary_before_official_lists() -> None:
    competition = parse_fixture_file("tests/fixtures/rgrtu/competition_list_full.json")[0]

    estimate = estimate_competition(competition, 195, today=date(2026, 6, 29))

    assert estimate.preliminary is True


def test_estimator_preserves_source_status() -> None:
    competition = parse_fixture_file("tests/fixtures/rgrtu/competition_list_full.json")[0]
    competition.rows = []
    competition.raw = {"error": "response does not contain HTML"}
    competition.source_status = SourceStatus.SCHEMA_CHANGED

    estimate = estimate_competition(competition, 195, today=date(2026, 6, 29))

    assert estimate.zone == AdmissionZone.SOURCE_UNAVAILABLE
    assert estimate.source_status == SourceStatus.SCHEMA_CHANGED
    assert estimate.source_error == "response does not contain HTML"
