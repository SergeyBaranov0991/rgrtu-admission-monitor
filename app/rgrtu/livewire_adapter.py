from __future__ import annotations

import hashlib
import html
import json
import re
from typing import Any

import httpx

from app.config import PROGRAMS, ProgramConfig, Settings
from app.rgrtu.base import CompetitionList, Funding, SourceStatus
from app.rgrtu.parser import parse_competition_payload, parse_competition_table_html


COMPONENT_NAME = "competition-lists-common"
BUDGET_COMPETITION_CODE = "04"
PAID_COMPETITION_CODE = "06"
INITIAL_DATA_RE = re.compile(r'wire:initial-data="([^"]*)"')
LIVEWIRE_TOKEN_RE = re.compile(r"window\.livewire_token = '([^']+)'")


class SourceSchemaError(RuntimeError):
    """Raised when the public RGRTU page is reachable but its data shape is unexpected."""


class RgrtuLivewireListAdapter:
    """Fetches public RGRTU competition lists from the overview Livewire payload."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.rgrtu_base_url.rstrip("/")
        self.page_url = f"{self.base_url}/guest/competition-lists/{settings.rgrtu_campaign_id}"
        self.endpoint_url = f"{self.base_url}/livewire/message/{COMPONENT_NAME}"

    async def fetch_tracked_competitions(self) -> list[CompetitionList]:
        async with httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": self.settings.user_agent},
            verify=self.settings.rgrtu_verify_ssl,
        ) as client:
            response = await client.get(self.page_url)
            response.raise_for_status()
            component = extract_livewire_component(response.text)
            memo_data = extract_livewire_memo_data(component)
            competition_payloads = extract_competitions_from_memo(memo_data)

            competitions: list[CompetitionList] = []
            for program in PROGRAMS:
                for funding in (Funding.BUDGET, Funding.PAID):
                    competitions.append(
                        self._build_tracked_competition(competition_payloads, program, funding)
                    )
            return competitions

    def _build_tracked_competition(
        self,
        competition_payloads: list[dict[str, Any]],
        program: ProgramConfig,
        funding: Funding,
    ) -> CompetitionList:
        try:
            payload = select_tracked_competition(competition_payloads, program, funding)
            competition_id = str(payload["id"])
        except (KeyError, SourceSchemaError) as exc:
            competition = build_empty_competition(
                program=program,
                funding=funding,
                campaign_id=self.settings.rgrtu_campaign_id,
                source_url=self._source_url(program, funding),
                raw={"error": str(exc)},
            )
            competition.source_status = SourceStatus.SCHEMA_CHANGED
            return competition

        return parse_competition_payload(
            payload,
            program_code=program.code,
            program_name=program.name,
            funding_type=funding,
            places=program.general_places if funding == Funding.BUDGET else program.paid_places,
            source_url=self._competition_source_url(competition_id),
            campaign_id=self.settings.rgrtu_campaign_id,
        )

    def _source_url(self, program: ProgramConfig, funding: Funding) -> str:
        funding_code = competition_code_for_funding(funding)
        return (
            f"{self.page_url}"
            f"?subject={program.subject_id or ''}"
            f"&study_form=full_time"
            f"&competition_type={funding_code}"
        )

    def _competition_source_url(self, competition_id: str) -> str:
        return f"{self.page_url}/{competition_id}"


def extract_competitions_from_memo(memo_data: dict[str, Any]) -> list[dict[str, Any]]:
    competitions = memo_data.get("competitions")
    if not isinstance(competitions, list):
        raise SourceSchemaError("Livewire memo does not contain competitions")
    if not all(isinstance(item, dict) for item in competitions):
        raise SourceSchemaError("Livewire competitions payload has unexpected items")
    return competitions


def select_tracked_competition(
    competitions: list[dict[str, Any]],
    program: ProgramConfig,
    funding: Funding,
) -> dict[str, Any]:
    competition_code = competition_code_for_funding(funding)
    places = program.general_places if funding == Funding.BUDGET else program.paid_places
    candidates = [
        competition
        for competition in competitions
        if _matches_program(competition, program)
        and str(competition.get("code") or "") == competition_code
        and str(competition.get("eduProgramFormCode") or "") == "1"
    ]
    exact_place_candidates = [
        competition for competition in candidates if _int_or_none(competition.get("plan")) == places
    ]
    selected = exact_place_candidates or candidates
    if len(selected) != 1:
        raise SourceSchemaError(
            f"Expected one competition for {program.code}/{funding.value}, found {len(selected)}"
        )
    return selected[0]


def competition_code_for_funding(funding: Funding) -> str:
    return BUDGET_COMPETITION_CODE if funding == Funding.BUDGET else PAID_COMPETITION_CODE


def _matches_program(competition: dict[str, Any], program: ProgramConfig) -> bool:
    title = str(competition.get("programSetPrintTitle") or "")
    if title.startswith(program.code):
        return True
    edu_programs = competition.get("eduPrograms")
    if not isinstance(edu_programs, list):
        return False
    return any(
        isinstance(item, dict)
        and str(item.get("fullTitleWithoutSubjectIndex") or "").startswith(program.code)
        for item in edu_programs
    )


def _int_or_none(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def extract_livewire_token(page_html: str) -> str:
    match = LIVEWIRE_TOKEN_RE.search(page_html)
    if match is None:
        raise SourceSchemaError("Livewire token was not found")
    return match.group(1)


def extract_livewire_component(page_html: str, component_name: str = COMPONENT_NAME) -> dict[str, Any]:
    for match in INITIAL_DATA_RE.finditer(page_html):
        try:
            data = json.loads(html.unescape(match.group(1)))
        except json.JSONDecodeError:
            continue
        if data.get("fingerprint", {}).get("name") == component_name:
            return data
    raise SourceSchemaError(f"{component_name} Livewire component was not found")


def extract_livewire_response_html(response_data: dict[str, Any]) -> str:
    effects = response_data.get("effects")
    if not isinstance(effects, dict):
        raise SourceSchemaError("Livewire response does not contain effects")
    html_value = effects.get("html")
    if not isinstance(html_value, str):
        raise SourceSchemaError("Livewire response does not contain HTML")
    return html_value


def extract_livewire_memo_data(response_data: dict[str, Any]) -> dict[str, Any]:
    server_memo = response_data.get("serverMemo")
    if not isinstance(server_memo, dict):
        raise SourceSchemaError("Livewire response does not contain serverMemo")
    memo_data = server_memo.get("data")
    if not isinstance(memo_data, dict):
        raise SourceSchemaError("Livewire response does not contain serverMemo.data")
    return memo_data


def build_filter_updates(subject_id: str, funding: Funding) -> list[dict[str, Any]]:
    competition_type_index = 3 if funding == Funding.BUDGET else 4
    return [
        {
            "type": "callMethod",
            "payload": {
                "id": "subject",
                "method": "$set",
                "params": ["subject", subject_id],
            },
        },
        {
            "type": "syncInput",
            "payload": {
                "id": "study-form",
                "name": "eduProgramForms.0.checked",
                # This is the exact value sent by the public UI for the "Очная" checkbox.
                "value": "2",
            },
        },
        {
            "type": "syncInput",
            "payload": {
                "id": "competition-type",
                "name": f"competitionTypes.{competition_type_index}.checked",
                "value": True,
            },
        },
    ]


def build_empty_competition(
    *,
    program: ProgramConfig,
    funding: Funding,
    campaign_id: int,
    source_url: str,
    raw: dict[str, Any] | None = None,
) -> CompetitionList:
    html_payload = ""
    competition = parse_competition_table_html(
        html_payload,
        program_code=program.code,
        program_name=program.name,
        funding_type=funding,
        places=program.general_places if funding == Funding.BUDGET else program.paid_places,
        source_url=source_url,
    )
    competition.metadata.campaign_id = campaign_id
    competition.metadata.source_hash = hashlib.sha256(html_payload.encode("utf-8")).hexdigest()
    competition.raw = raw
    return competition
