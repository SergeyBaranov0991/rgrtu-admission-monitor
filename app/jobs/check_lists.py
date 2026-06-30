from __future__ import annotations

from pathlib import Path
import logging

import httpx

from app.admission.estimator import AdmissionEstimate, estimate_competition
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


async def load_live_competitions(settings: Settings) -> list[CompetitionList]:
    return await RgrtuLivewireListAdapter(settings).fetch_tracked_competitions()


async def estimate_from_live(score: int, settings: Settings) -> list[AdmissionEstimate]:
    try:
        competitions = await load_live_competitions(settings)
    except SourceSchemaError as exc:
        logger.exception("rgrtu_live_schema_changed")
        competitions = unavailable_competitions(settings, error=exc, source_status=SourceStatus.SCHEMA_CHANGED)
    except httpx.HTTPError as exc:
        logger.exception("rgrtu_live_fetch_failed")
        competitions = unavailable_competitions(settings, error=exc, source_status=SourceStatus.UNAVAILABLE)
    except Exception as exc:
        logger.exception("rgrtu_live_fetch_failed")
        competitions = unavailable_competitions(settings, error=exc, source_status=SourceStatus.UNAVAILABLE)
    return [estimate_competition(competition, score) for competition in competitions]


def unavailable_competitions(
    settings: Settings,
    *,
    error: Exception | None = None,
    source_status: SourceStatus = SourceStatus.UNAVAILABLE,
) -> list[CompetitionList]:
    competitions: list[CompetitionList] = []
    base_url = settings.rgrtu_base_url.rstrip("/")
    for program in PROGRAMS:
        for funding in (Funding.BUDGET, Funding.PAID):
            source_url = (
                f"{base_url}/guest/entrant-lists/{settings.rgrtu_campaign_id}"
                f"?subject={program.subject_id or ''}"
                f"&study_form=full_time"
                f"&competition_type={'04' if funding == Funding.BUDGET else '06'}"
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
