from app.config import Settings
from app.jobs import check_lists
from app.jobs.check_lists import estimate_relative_competitions
from app.rgrtu.base import ApplicantRow, CompetitionList, CompetitionMetadata, Funding


async def test_code_relative_loads_all_full_time_competitions(monkeypatch) -> None:
    calls: list[str] = []

    async def fake_load_all_full_time_competitions(settings: Settings) -> list:
        calls.append("all")
        return []

    async def fake_load_live_competitions(
        settings: Settings,
        *,
        category_scope: str = "general",
    ) -> list:
        calls.append("tracked")
        return []

    monkeypatch.setattr(
        check_lists,
        "load_all_full_time_competitions",
        fake_load_all_full_time_competitions,
    )
    monkeypatch.setattr(check_lists, "load_live_competitions", fake_load_live_competitions)

    await check_lists.estimate_from_live(
        195,
        Settings(),
        entrant_code="1158236",
        relative=True,
    )

    assert calls == ["all"]


def test_relative_estimate_keeps_source_decision_data_counts() -> None:
    higher = CompetitionList(
        metadata=CompetitionMetadata(
            program_code="09.03.02",
            program_name="Информационные системы и технологии",
            funding_type=Funding.BUDGET,
            published_places=1,
            applications_count=1,
        ),
        rows=[
            ApplicantRow(
                anonymous_applicant_id="applicant-1",
                total_score=300,
                priority=1,
            )
        ],
    )
    lower = CompetitionList(
        metadata=CompetitionMetadata(
            program_code="02.03.02",
            program_name="Фундаментальная информатика",
            funding_type=Funding.BUDGET,
            published_places=1,
            applications_count=2,
        ),
        rows=[
            ApplicantRow(
                anonymous_applicant_id="applicant-1",
                total_score=300,
                priority=2,
                higher_priority_status="ВПП",
            ),
            ApplicantRow(
                anonymous_applicant_id="applicant-2",
                total_score=195,
                priority=1,
            ),
        ],
    )

    estimates = estimate_relative_competitions([higher, lower], 195)

    lower_estimate = estimates[1]
    assert lower_estimate.relative_rows_count == 1
    assert lower_estimate.decision_rows_count == 1
    assert lower_estimate.higher_priority_status_rows_count == 1
