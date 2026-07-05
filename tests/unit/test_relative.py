from app.admission.relative import build_relative_selection
from app.admission.zones import AdmissionZone
from app.jobs.check_lists import estimate_relative_competitions
from app.rgrtu.base import ApplicantRow, CompetitionList, CompetitionMetadata, Funding


def _competition(
    code: str,
    *,
    places: int,
    rows: list[ApplicantRow],
) -> CompetitionList:
    return CompetitionList(
        metadata=CompetitionMetadata(
            program_code=code,
            program_name=f"Направление {code}",
            funding_type=Funding.BUDGET,
            published_places=places,
            applications_count=len(rows),
        ),
        rows=rows,
    )


def test_relative_selection_excludes_applicant_passing_higher_priority() -> None:
    higher = _competition(
        "01.03.02",
        places=1,
        rows=[
            ApplicantRow(anonymous_applicant_id="a", total_score=250, priority=1),
            ApplicantRow(anonymous_applicant_id="b", total_score=240, priority=1),
        ],
    )
    current = _competition(
        "09.03.03",
        places=2,
        rows=[
            ApplicantRow(anonymous_applicant_id="a", total_score=250, priority=2),
            ApplicantRow(anonymous_applicant_id="b", total_score=240, priority=2),
            ApplicantRow(anonymous_applicant_id="target", total_score=230, priority=2),
        ],
    )

    selection = build_relative_selection([higher, current])

    assert [row.anonymous_applicant_id for row in selection.competitions[1].rows] == [
        "b",
        "target",
    ]
    assert (1, "a") in selection.exclusions
    assert (1, "b") not in selection.exclusions


def test_relative_estimate_uses_filtered_position_for_target_code() -> None:
    higher = _competition(
        "01.03.02",
        places=1,
        rows=[
            ApplicantRow(anonymous_applicant_id="a", total_score=250, priority=1),
            ApplicantRow(anonymous_applicant_id="b", total_score=240, priority=1),
        ],
    )
    current = _competition(
        "09.03.03",
        places=2,
        rows=[
            ApplicantRow(anonymous_applicant_id="a", position=1, total_score=250, priority=2),
            ApplicantRow(anonymous_applicant_id="b", position=2, total_score=240, priority=2),
            ApplicantRow(anonymous_applicant_id="target", position=3, total_score=230, priority=2),
        ],
    )

    estimate = estimate_relative_competitions(
        [higher, current],
        100,
        entrant_code="target",
    )[1]

    assert estimate.ranking_mode == "relative"
    assert estimate.raw_position == (2, 2)
    assert estimate.relative_rows_count == 2
    assert estimate.target_priority == 2
    assert estimate.zone == AdmissionZone.PASSING


def test_relative_estimate_marks_target_passing_higher_priority() -> None:
    higher = _competition(
        "01.03.02",
        places=1,
        rows=[
            ApplicantRow(anonymous_applicant_id="target", total_score=250, priority=1),
            ApplicantRow(anonymous_applicant_id="b", total_score=240, priority=1),
        ],
    )
    current = _competition(
        "09.03.03",
        places=2,
        rows=[
            ApplicantRow(anonymous_applicant_id="target", total_score=250, priority=2),
            ApplicantRow(anonymous_applicant_id="b", total_score=240, priority=2),
        ],
    )

    estimate = estimate_relative_competitions(
        [higher, current],
        100,
        entrant_code="target",
    )[1]

    assert estimate.zone == AdmissionZone.HIGHER_PRIORITY
    assert estimate.raw_position is None
    assert estimate.target_found is True
    assert estimate.relative_excluded_by == "01.03.02 Направление 01.03.02 - бюджет"
