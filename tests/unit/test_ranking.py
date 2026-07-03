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
    assert score_rank_interval(rows, 195).worst == 4


def test_score_rank_interval_ignores_non_competing_statuses() -> None:
    rows = [
        ApplicantRow(total_score=276, application_status="Участвует в конкурсе"),
        ApplicantRow(total_score=246, application_status="Сданы ВИ"),
        ApplicantRow(total_score=215, application_status="Участвует в конкурсе"),
        ApplicantRow(total_score=195, application_status="Участвует в конкурсе"),
        ApplicantRow(total_score=183, application_status="Участвует в конкурсе"),
    ]

    interval = score_rank_interval(rows, 195)

    assert interval.best == 3
    assert interval.worst == 3


def test_passing_score_uses_last_available_place() -> None:
    rows = [ApplicantRow(total_score=210), ApplicantRow(total_score=200), ApplicantRow(total_score=195)]

    assert passing_score(rows, 2) == 200
