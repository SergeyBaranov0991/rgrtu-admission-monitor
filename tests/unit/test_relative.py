from app.admission.relative import build_relative_selection
from app.admission.zones import AdmissionZone
from app.jobs.check_lists import estimate_relative_competitions
from app.rgrtu.base import ApplicantRow, CompetitionList, CompetitionMetadata, Funding


def _competition(
    code: str,
    *,
    places: int,
    rows: list[ApplicantRow],
    funding: Funding = Funding.BUDGET,
) -> CompetitionList:
    return CompetitionList(
        metadata=CompetitionMetadata(
            program_code=code,
            program_name=f"Направление {code}",
            funding_type=funding,
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


def test_relative_estimate_keeps_target_in_lower_priority_lists() -> None:
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

    assert estimate.zone == AdmissionZone.PASSING
    assert estimate.raw_position == (1, 1)
    assert estimate.target_found is True
    assert estimate.target_priority == 2
    assert estimate.relative_excluded_by is None


def test_relative_estimate_keeps_lower_priority_rows_until_they_pass_higher() -> None:
    current = _competition(
        "09.03.03",
        places=2,
        rows=[
            ApplicantRow(anonymous_applicant_id="priority-1", total_score=260, priority=1),
            ApplicantRow(anonymous_applicant_id="lower-priority", total_score=250, priority=4),
            ApplicantRow(anonymous_applicant_id="target", total_score=230, priority=3),
        ],
    )

    estimate = estimate_relative_competitions(
        [current],
        100,
        entrant_code="target",
    )[0]

    assert estimate.raw_position == (3, 3)
    assert estimate.relative_rows_count == 3


def test_relative_estimate_excludes_lower_priority_row_when_it_passes_higher() -> None:
    higher = _competition(
        "01.03.02",
        places=1,
        rows=[
            ApplicantRow(anonymous_applicant_id="lower-priority", total_score=250, priority=1),
            ApplicantRow(anonymous_applicant_id="other", total_score=240, priority=1),
        ],
    )
    current = _competition(
        "09.03.03",
        places=2,
        rows=[
            ApplicantRow(anonymous_applicant_id="priority-1", total_score=260, priority=1),
            ApplicantRow(anonymous_applicant_id="lower-priority", total_score=250, priority=4),
            ApplicantRow(anonymous_applicant_id="target", total_score=230, priority=3),
        ],
    )

    estimate = estimate_relative_competitions(
        [higher, current],
        100,
        entrant_code="target",
    )[1]

    assert estimate.raw_position == (2, 2)
    assert estimate.relative_rows_count == 2


def test_relative_selection_does_not_mix_budget_and_paid_priorities() -> None:
    paid = _competition(
        "09.03.03",
        places=1,
        funding=Funding.PAID,
        rows=[
            ApplicantRow(anonymous_applicant_id="a", total_score=250, priority=1),
        ],
    )
    budget = _competition(
        "09.03.03",
        places=1,
        funding=Funding.BUDGET,
        rows=[
            ApplicantRow(anonymous_applicant_id="a", total_score=250, priority=2),
        ],
    )

    selection = build_relative_selection([paid, budget])

    assert [row.anonymous_applicant_id for row in selection.competitions[1].rows] == ["a"]
    assert (1, "a") not in selection.exclusions


def test_relative_estimate_uses_filtered_list_order_for_target_code() -> None:
    higher = _competition(
        "01.03.02",
        places=1,
        rows=[
            ApplicantRow(anonymous_applicant_id="excluded", total_score=260, priority=1),
        ],
    )
    current = _competition(
        "09.03.03",
        places=2,
        rows=[
            ApplicantRow(anonymous_applicant_id="excluded", position=1, total_score=260, priority=2),
            ApplicantRow(anonymous_applicant_id="target", position=2, total_score=230, priority=2),
            ApplicantRow(anonymous_applicant_id="tie", position=3, total_score=230, priority=2),
        ],
    )

    estimate = estimate_relative_competitions(
        [higher, current],
        100,
        entrant_code="target",
    )[1]

    assert estimate.raw_position == (1, 1)
    assert estimate.relative_rows_count == 2
