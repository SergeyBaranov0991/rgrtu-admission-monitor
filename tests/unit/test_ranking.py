from app.admission.ranking import passing_score, score_rank_interval
from app.rgrtu.base import ApplicantRow


def test_score_rank_interval_handles_equal_scores() -> None:
    rows = [
        ApplicantRow(total_score=210),
        ApplicantRow(total_score=200),
        ApplicantRow(total_score=195),
        ApplicantRow(total_score=195),
        ApplicantRow(total_score=190),
    ]

    assert score_rank_interval(rows, 195).best == 3
    assert score_rank_interval(rows, 195).worst == 5


def test_passing_score_uses_last_available_place() -> None:
    rows = [ApplicantRow(total_score=210), ApplicantRow(total_score=200), ApplicantRow(total_score=195)]

    assert passing_score(rows, 2) == 200

