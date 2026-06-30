from __future__ import annotations

import asyncio
import copy
import hashlib
import html
import json
import re
from dataclasses import dataclass
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.config import PROGRAMS, ProgramConfig, Settings
from app.rgrtu.base import CompetitionList, Funding, SourceStatus
from app.rgrtu.parser import parse_competition_table_html


COMPONENT_NAME = "competition-lists-common"
LIVEWIRE_TOKEN_RE = re.compile(r"window\.livewire_token = '([^']+)'")


class SourceSchemaError(RuntimeError):
    """Raised when the public RGRTU page is reachable but its data shape is unexpected."""


@dataclass(frozen=True)
class LivewireInitialState:
    page_url: str
    token: str
    component: dict[str, Any]


class RgrtuLivewireListAdapter:
    """Fetches public RGRTU entrant list pages through their Livewire endpoint."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.rgrtu_base_url.rstrip("/")
        self.page_url = f"{self.base_url}/guest/entrant-lists/{settings.rgrtu_campaign_id}"
        self.endpoint_url = f"{self.base_url}/livewire/message/{COMPONENT_NAME}"

    async def fetch_tracked_competitions(self) -> list[CompetitionList]:
        async with httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": self.settings.user_agent},
            verify=self.settings.rgrtu_verify_ssl,
        ) as client:
            initial = await self._load_initial_state(client)
            competitions: list[CompetitionList] = []
            for program in PROGRAMS:
                competitions.append(
                    await self._fetch_filtered_competition(client, initial, program, Funding.BUDGET)
                )
                await asyncio.sleep(0.2)
                competitions.append(
                    await self._fetch_filtered_competition(client, initial, program, Funding.PAID)
                )
                await asyncio.sleep(0.2)
            return competitions

    async def _load_initial_state(self, client: httpx.AsyncClient) -> LivewireInitialState:
        response = await client.get(self.page_url)
        response.raise_for_status()
        token = extract_livewire_token(response.text)
        component = extract_livewire_component(response.text)
        return LivewireInitialState(page_url=str(response.url), token=token, component=component)

    async def _fetch_filtered_competition(
        self,
        client: httpx.AsyncClient,
        initial: LivewireInitialState,
        program: ProgramConfig,
        funding: Funding,
    ) -> CompetitionList:
        if program.subject_id is None:
            competition = build_empty_competition(
                program=program,
                funding=funding,
                campaign_id=self.settings.rgrtu_campaign_id,
                source_url=self._source_url(program, funding),
                raw={"error": "subject_id is not configured"},
            )
            competition.source_status = SourceStatus.SCHEMA_CHANGED
            return competition

        component = copy.deepcopy(initial.component)
        payload = {
            "fingerprint": component["fingerprint"],
            "serverMemo": component["serverMemo"],
            "updates": build_filter_updates(program.subject_id, funding),
        }
        response = await client.post(
            self.endpoint_url,
            headers={
                "Content-Type": "application/json",
                "Accept": "text/html, application/xhtml+xml",
                "X-Livewire": "true",
                "X-CSRF-TOKEN": initial.token,
                "Referer": initial.page_url,
            },
            json=payload,
        )
        response.raise_for_status()
        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise SourceSchemaError("Livewire response is not valid JSON") from exc

        response_html = extract_livewire_response_html(data)
        memo_data = extract_livewire_memo_data(data)
        competition = parse_competition_table_html(
            response_html,
            program_code=program.code,
            program_name=program.name,
            funding_type=funding,
            places=program.general_places if funding == Funding.BUDGET else program.paid_places,
            source_url=self._source_url(program, funding),
        )
        competition.metadata.campaign_id = self.settings.rgrtu_campaign_id
        competition.raw = {
            "page_url": initial.page_url,
            "endpoint_url": self.endpoint_url,
            "program_subject_id": program.subject_id,
            "funding": funding.value,
            "livewire_server_memo_keys": sorted(memo_data.keys()),
            "livewire_competitions_count": len(memo_data.get("competitions") or []),
        }
        return competition

    def _source_url(self, program: ProgramConfig, funding: Funding) -> str:
        funding_code = "04" if funding == Funding.BUDGET else "06"
        return (
            f"{self.page_url}"
            f"?subject={program.subject_id or ''}"
            f"&study_form=full_time"
            f"&competition_type={funding_code}"
        )


def extract_livewire_token(page_html: str) -> str:
    match = LIVEWIRE_TOKEN_RE.search(page_html)
    if match is None:
        raise SourceSchemaError("Livewire token was not found")
    return match.group(1)


def extract_livewire_component(page_html: str, component_name: str = COMPONENT_NAME) -> dict[str, Any]:
    soup = BeautifulSoup(page_html, "lxml")
    for element in soup.select("[wire\\:initial-data]"):
        try:
            data = json.loads(html.unescape(element["wire:initial-data"]))
        except (KeyError, json.JSONDecodeError):
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
