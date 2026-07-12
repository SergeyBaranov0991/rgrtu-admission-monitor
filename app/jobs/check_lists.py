from __future__ import annotations

from pathlib import Path
import logging

import httpx

from app.admission.estimator import (
    AdmissionEstimate,
    decision_data_counts,
    estimate_competition,
    estimate_competition_by_code,
)
from app.admission.relative import (
    RelativeSelection,
    build_relative_selection,
    find_row_by_applicant_id,
    relative_rows_count,
)
from app.config import PROGRAMS, Settings
from app.rgrtu.base import CompetitionList, Funding, SourceStatus
from app.rgrtu.livewire_adapter import RgrtuLivewireListAdapter, SourceSchemaError, build_empty_competition
from app.rgrtu.parser import parse_fixture_file


DEFAULT_FIXTURE = Path("tests/fixtures/rgrtu/competition_list_full.json")
logger = logging.getLogger(__name__)


def load_dev_fixture(path: Path = DEFAULT_FIXTURE) -> list[CompetitionList]:
    return parse_fixture_file(str(path))


def estimate_from_fixture(score: int, fixture_path: Path = DEFAULT_FIXTURE) -> list[AdmissionEstimate]:
    competitions = load_dev_fixture(fixture_path)
    return [estimate_competition(competition, score) for competition in competitions]


async def load_live_competitions(
    settings: Settings,
    *,
    category_scope: str = "general",
) -> list[CompetitionList]:
    return await RgrtuLivewireListAdapter(settings).fetch_tracked_competitions(
        category_scope=category_scope,
    )


async def load_all_full_time_competitions(settings: Settings) -> list[CompetitionList]:
    return await RgrtuLivewireListAdapter(settings).fetch_all_full_time_competitions()


async def estimate_from_live(
    score: int,
    settings: Settings,
    *,
    category_scope: str = "general",
    entrant_code: str | None = None,
    relative: bool = False,
    search_all_full_time: bool = False,
) -> list[AdmissionEstimate]:
    load_all_full_time = search_all_full_time or bool(relative and entrant_code)
    try:
        competitions = (
            await load_all_full_time_competitions(settings)
            if load_all_full_time
            else await load_live_competitions(settings, category_scope=category_scope)
        )
    except SourceSchemaError as exc:
        logger.exception("rgrtu_live_schema_changed")
        competitions = unavailable_competitions(
            settings,
            error=exc,
            source_status=SourceStatus.SCHEMA_CHANGED,
            category_scope=category_scope,
        )
    except httpx.HTTPError as exc:
        logger.exception("rgrtu_live_fetch_failed")
        competitions = unavailable_competitions(
            settings,
            error=exc,
            source_status=SourceStatus.UNAVAILABLE,
            category_scope=category_scope,
        )
    except Exception as exc:
        logger.exception("rgrtu_live_fetch_failed")
        competitions = unavailable_competitions(
            settings,
            error=exc,
            source_status=SourceStatus.UNAVAILABLE,
            category_scope=category_scope,
        )
    if relative:
        return estimate_relative_competitions(
            competitions,
            score,
            entrant_code=entrant_code,
        )
    if entrant_code:
        return [
            estimate_competition_by_code(competition, entrant_code, fallback_score=score)
            for competition in competitions
        ]
    return [estimate_competition(competition, score) for competition in competitions]


def estimate_relative_competitions(
    competitions: list[CompetitionList],
    score: int,
    *,
    entrant_code: str | None = None,
) -> list[AdmissionEstimate]:
    selection = build_relative_selection(competitions)
    estimates: list[AdmissionEstimate] = []
    for index, original in enumerate(competitions):
        original_target = (
            find_row_by_applicant_id(original, entrant_code)
            if entrant_code is not None
            else None
        )
        if entrant_code and original_target is not None:
            filtered = _target_relative_competition(
                original,
                selection=selection,
                competition_index=index,
                entrant_code=entrant_code,
            )
            estimate = estimate_competition_by_code(
                filtered,
                entrant_code,
                fallback_score=score,
                use_row_position=False,
                use_filtered_order_position=True,
            ).model_copy(
                update={
                    "target_priority": original_target.priority,
                }
            )
        elif entrant_code:
            filtered = selection.competitions[index]
            estimate = estimate_competition_by_code(
                filtered,
                entrant_code,
                fallback_score=score,
                use_row_position=False,
            ).model_copy(
                update={
                    "target_priority": original_target.priority if original_target else None,
                }
            )
        else:
            filtered = selection.competitions[index]
            estimate = estimate_competition(filtered, score)

        estimates.append(
            estimate.model_copy(
                update={
                    "ranking_mode": "relative",
                    "relative_rows_count": (
                        relative_rows_count(filtered)
                        if filtered.source_status == SourceStatus.OK
                        else None
                    ),
                    **_decision_data_update(original),
                }
            )
        )
    return estimates


def _decision_data_update(competition: CompetitionList) -> dict[str, int]:
    counts = decision_data_counts(competition)
    return {
        "decision_rows_count": counts["decision"],
        "consent_rows_count": counts["consent"],
        "original_rows_count": counts["original"],
        "higher_priority_status_rows_count": counts["higher_priority_status"],
    }


def _target_relative_competition(
    competition: CompetitionList,
    *,
    selection: RelativeSelection,
    competition_index: int,
    entrant_code: str,
) -> CompetitionList:
    rows = []
    for row in competition.rows:
        key = row.anonymous_applicant_id
        if not row.is_active or key is None:
            continue
        if key == entrant_code:
            rows.append(row)
            continue
        if (competition_index, key) in selection.exclusions:
            continue
        rows.append(row)
    return competition.model_copy(update={"rows": rows})


def unavailable_competitions(
    settings: Settings,
    *,
    error: Exception | None = None,
    source_status: SourceStatus = SourceStatus.UNAVAILABLE,
    category_scope: str = "general",
) -> list[CompetitionList]:
    competitions: list[CompetitionList] = []
    base_url = settings.rgrtu_base_url.rstrip("/")
    for program in PROGRAMS:
        fundings = (Funding.BUDGET, Funding.PAID) if category_scope == "all" else (Funding.BUDGET,)
        for funding in fundings:
            competition_type = "04" if funding == Funding.BUDGET else "06"
            source_url = (
                f"{base_url}/guest/competition-lists/{settings.rgrtu_campaign_id}"
                f"?subject={program.subject_id or ''}"
                f"&study_form=full_time"
                f"&competition_type={competition_type}"
            )
            competition = build_empty_competition(
                program=program,
                funding=funding,
                campaign_id=settings.rgrtu_campaign_id,
                source_url=source_url,
                raw={"error": str(error)} if error else None,
            )
            competition.source_status = source_status
            competitions.append(competition)
    return competitions


def missing_competitions(competitions: list[CompetitionList]) -> list[tuple[str, Funding]]:
    existing = {
        (competition.metadata.program_code, competition.metadata.funding_type)
        for competition in competitions
    }
    missing: list[tuple[str, Funding]] = []
    for program in PROGRAMS:
        for funding in (Funding.BUDGET, Funding.PAID):
            if (program.code, funding) not in existing:
                missing.append((program.code, funding))
    return missing
