from __future__ import annotations

from app.config import PROGRAMS, ProgramConfig, Settings
from app.rgrtu.discovery import SubjectDiscovery, discover_subjects


class RgrtuLivewireAdapter:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def discover(self) -> SubjectDiscovery:
        return await discover_subjects(
            self.settings.rgrtu_base_url,
            self.settings.rgrtu_campaign_id,
            self.settings.user_agent,
            verify_ssl=self.settings.rgrtu_verify_ssl,
        )

    async def verify_tracked_subjects(self) -> dict[str, bool]:
        discovery = await self.discover()
        discovered_values = set(discovery.subjects.values())
        return {
            program.code: any(value.startswith(program.code) for value in discovered_values)
            for program in PROGRAMS
        }


def tracked_subject_ids() -> dict[str, str | None]:
    return {program.code: program.subject_id for program in PROGRAMS}


def program_places(program: ProgramConfig, funding_type: str) -> int:
    return program.general_places if funding_type == "budget" else program.paid_places
