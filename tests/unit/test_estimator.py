from datetime import date

from app.admission.estimator import estimate_competition
from app.admission.zones import AdmissionZone
from app.rgrtu.base import ApplicantRow, CompetitionList, CompetitionMetadata, Funding, SourceStatus
from app.rgrtu.parser import parse_fixture_file


def test_estimator_marks_borderline_interval() -> None:
    competition = parse_fixture_file("tests/fixtures/rgrtu/competition_list_full.json")[0]

    estimate = estimate_competition(competition, 195, today=date(2026, 7, 29))

    assert estimate.zone == AdmissionZone.PASSING
    assert estimate.raw_position == (16, 17)
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


def test_estimator_uses_raw_position_and_passing_score() -> None:
    competition = CompetitionList(
        metadata=CompetitionMetadata(
            program_code="09.03.03",
            program_name="Прикладная информатика",
            funding_type=Funding.BUDGET,
            published_places=2,
            applications_count=4,
        ),
        rows=[
            ApplicantRow(total_score=240, priority=3),
            ApplicantRow(total_score=230, priority=3),
            ApplicantRow(total_score=195, priority=1),
            ApplicantRow(total_score=190, priority=1),
        ],
    )

    estimate = estimate_competition(competition, 195, today=date(2026, 7, 3))

    assert estimate.raw_position == (3, 3)
    assert estimate.effective_position == (1, 1)
    assert estimate.current_passing_score == 230
    assert estimate.zone == AdmissionZone.BORDERLINE


def test_estimator_marks_incomplete_scores_as_insufficient_data() -> None:
    competition = CompetitionList(
        metadata=CompetitionMetadata(
            program_code="09.03.03",
            program_name="Прикладная информатика",
            funding_type=Funding.BUDGET,
            published_places=3,
            applications_count=5,
        ),
        rows=[
            ApplicantRow(total_score=240),
            ApplicantRow(total_score=195),
            ApplicantRow(total_score=None),
            ApplicantRow(total_score=None),
            ApplicantRow(total_score=None),
        ],
    )

    estimate = estimate_competition(competition, 195, today=date(2026, 7, 3))

    assert estimate.raw_position == (2, 2)
    assert estimate.scored_rows_count == 2
    assert estimate.current_passing_score is None
    assert estimate.forecast_passing_score is None
    assert estimate.zone == AdmissionZone.INSUFFICIENT_DATA
    assert estimate.confidence < 0.5
