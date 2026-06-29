from __future__ import annotations

from pathlib import Path

from app.admission.estimator import AdmissionEstimate, estimate_competition
from app.config import PROGRAMS
from app.rgrtu.base import CompetitionList, Funding
from app.rgrtu.parser import parse_fixture_file


DEFAULT_FIXTURE = Path("tests/fixtures/rgrtu/competition_list_full.json")


def load_dev_fixture(path: Path = DEFAULT_FIXTURE) -> list[CompetitionList]:
    return parse_fixture_file(str(path))


def estimate_from_fixture(score: int, fixture_path: Path = DEFAULT_FIXTURE) -> list[AdmissionEstimate]:
    competitions = load_dev_fixture(fixture_path)
    return [estimate_competition(competition, score) for competition in competitions]


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

