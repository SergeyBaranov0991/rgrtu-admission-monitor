from __future__ import annotations

import asyncio
from dataclasses import dataclass
import hashlib
import html
import json
import re
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.config import PROGRAMS, ProgramConfig, Settings
from app.rgrtu.base import CompetitionList, Funding, SourceStatus
from app.rgrtu.parser import parse_competition_payload, parse_competition_table_html


COMPONENT_NAME = "competition-lists-common"
BUDGET_COMPETITION_CODE = "04"
PAID_COMPETITION_CODE = "06"
PAID_COMPETITION_CODES = {"05", "06"}
INITIAL_DATA_RE = re.compile(r'wire:initial-data="([^"]*)"')
LIVEWIRE_TOKEN_RE = re.compile(r"window\.livewire_token = '([^']+)'")
PROGRAM_TITLE_RE = re.compile(r"(?P<code>\d{2}\.\d{2}\.\d{2})\s*(?P<name>.*)")
COMPETITION_LINK_RE = re.compile(r"/guest/competition-lists/(?P<campaign_id>\d+)/(?P<competition_id>\d+)")
DIRECT_FETCH_CONCURRENCY = 8


@dataclass(frozen=True)
class CompetitionCard:
    competition_id: str
    source_url: str
    program_code: str
    program_name: str
    study_form: str
    funding_type: Funding
    admission_basis: str
    places: int
    applications_count: int | None
    withdrawn_count: int | None
    raw_text: str


class SourceSchemaError(RuntimeError):
    """Raised when the public RGRTU page is reachable but its data shape is unexpected."""


class RgrtuLivewireListAdapter:
    """Fetches public RGRTU competition lists from the overview Livewire payload."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.rgrtu_base_url.rstrip("/")
        self.page_url = f"{self.base_url}/guest/competition-lists/{settings.rgrtu_campaign_id}"
        self.endpoint_url = f"{self.base_url}/livewire/message/{COMPONENT_NAME}"

    async def fetch_tracked_competitions(self, *, category_scope: str = "general") -> list[CompetitionList]:
        overview_html = await self._fetch_overview_html()
        competition_payloads = self._competition_payloads_from_html(overview_html)
        if not competition_payloads:
            cards = extract_competition_cards(
                overview_html,
                campaign_id=self.settings.rgrtu_campaign_id,
                base_url=self.base_url,
            )
            return await self._fetch_tracked_competitions_from_cards(
                cards,
                category_scope=category_scope,
            )

        competitions: list[CompetitionList] = []
        for program in PROGRAMS:
            if category_scope == "all":
                competitions.extend(self._build_all_category_competitions(competition_payloads, program))
                continue
            competitions.append(
                self._build_tracked_competition(competition_payloads, program, Funding.BUDGET)
            )
        return competitions

    async def fetch_all_full_time_competitions(self) -> list[CompetitionList]:
        overview_html = await self._fetch_overview_html()
        competition_payloads = self._competition_payloads_from_html(overview_html)
        if not competition_payloads:
            cards = [
                card
                for card in extract_competition_cards(
                    overview_html,
                    campaign_id=self.settings.rgrtu_campaign_id,
                    base_url=self.base_url,
                )
                if card.study_form == "full_time"
            ]
            return await self._fetch_direct_competitions(cards)

        competitions: list[CompetitionList] = []
        for payload in competition_payloads:
            if str(payload.get("eduProgramFormCode") or "") != "1":
                continue
            program_info = program_info_for_competition_payload(payload)
            if program_info is None:
                continue
            program_code, program_name = program_info
            competition_id = str(payload["id"])
            competitions.append(
                parse_competition_payload(
                    payload,
                    program_code=program_code,
                    program_name=program_name,
                    funding_type=funding_for_competition_payload(payload),
                    places=_int_or_none(payload.get("plan")) or 0,
                    source_url=self._competition_source_url(competition_id),
                    campaign_id=self.settings.rgrtu_campaign_id,
                )
            )
        return competitions

    async def _fetch_overview_html(self) -> str:
        async with httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": self.settings.user_agent},
            verify=self.settings.rgrtu_verify_ssl,
        ) as client:
            response = await client.get(self.page_url)
            response.raise_for_status()
            return response.content.decode("utf-8", errors="replace")

    async def _fetch_competition_payloads(self) -> list[dict[str, Any]]:
        return self._competition_payloads_from_html(await self._fetch_overview_html())

    def _competition_payloads_from_html(self, page_html: str) -> list[dict[str, Any]]:
        component = extract_livewire_component(page_html)
        memo_data = extract_livewire_memo_data(component)
        return extract_competitions_from_memo(memo_data)

    async def _fetch_tracked_competitions_from_cards(
        self,
        cards: list[CompetitionCard],
        *,
        category_scope: str,
    ) -> list[CompetitionList]:
        competitions: list[CompetitionList] = []
        direct_cards: list[CompetitionCard] = []
        for program in PROGRAMS:
            if category_scope == "all":
                selected = select_profile_competition_cards(cards, program)
                if not selected:
                    competitions.append(
                        self._empty_competition_from_card_error(
                            program,
                            Funding.BUDGET,
                            f"Tracked profile for {program.code} was not found in overview cards",
                        )
                    )
                    continue
                direct_cards.extend(selected)
                continue
            try:
                direct_cards.append(select_tracked_competition_card(cards, program, Funding.BUDGET))
            except SourceSchemaError as exc:
                competitions.append(
                    self._empty_competition_from_card_error(program, Funding.BUDGET, str(exc))
                )

        competitions.extend(await self._fetch_direct_competitions(direct_cards))
        return competitions

    async def _fetch_direct_competitions(self, cards: list[CompetitionCard]) -> list[CompetitionList]:
        semaphore = asyncio.Semaphore(DIRECT_FETCH_CONCURRENCY)
        async with httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": self.settings.user_agent},
            verify=self.settings.rgrtu_verify_ssl,
        ) as client:
            return await asyncio.gather(
                *(self._fetch_direct_competition(client, semaphore, card) for card in cards)
            )

    async def _fetch_direct_competition(
        self,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
        card: CompetitionCard,
    ) -> CompetitionList:
        async with semaphore:
            response = await client.get(card.source_url)
            response.raise_for_status()
            page_html = response.content.decode("utf-8", errors="replace")
        return parse_competition_table_html(
            page_html,
            program_code=card.program_code,
            program_name=card.program_name,
            funding_type=card.funding_type,
            places=card.places,
            source_url=card.source_url,
            campaign_id=self.settings.rgrtu_campaign_id,
            competition_id=card.competition_id,
            admission_basis=card.admission_basis,
            applications_count=card.applications_count,
            withdrawn_count=card.withdrawn_count,
        )

    def _empty_competition_from_card_error(
        self,
        program: ProgramConfig,
        funding: Funding,
        error: str,
    ) -> CompetitionList:
        competition = build_empty_competition(
            program=program,
            funding=funding,
            campaign_id=self.settings.rgrtu_campaign_id,
            source_url=self._source_url(program, funding),
            raw={"error": error},
        )
        competition.source_status = SourceStatus.SCHEMA_CHANGED
        return competition

    def _build_all_category_competitions(
        self,
        competition_payloads: list[dict[str, Any]],
        program: ProgramConfig,
    ) -> list[CompetitionList]:
        try:
            selected_payloads = select_profile_competitions(competition_payloads, program)
        except SourceSchemaError as exc:
            competition = build_empty_competition(
                program=program,
                funding=Funding.BUDGET,
                campaign_id=self.settings.rgrtu_campaign_id,
                source_url=f"{self.page_url}?subject={program.subject_id or ''}",
                raw={"error": str(exc)},
            )
            competition.source_status = SourceStatus.SCHEMA_CHANGED
            return [competition]

        competitions: list[CompetitionList] = []
        for payload in selected_payloads:
            competition_id = str(payload["id"])
            funding = funding_for_competition_payload(payload)
            competitions.append(
                parse_competition_payload(
                    payload,
                    program_code=program.code,
                    program_name=program.name,
                    funding_type=funding,
                    places=_int_or_none(payload.get("plan")) or 0,
                    source_url=self._competition_source_url(competition_id),
                    campaign_id=self.settings.rgrtu_campaign_id,
                )
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


def select_profile_competitions(
    competitions: list[dict[str, Any]],
    program: ProgramConfig,
) -> list[dict[str, Any]]:
    anchors: list[dict[str, Any]] = []
    for funding in (Funding.BUDGET, Funding.PAID):
        try:
            anchors.append(select_tracked_competition(competitions, program, funding))
        except SourceSchemaError:
            continue
    profile_ids = {
        edu_program_id
        for anchor in anchors
        for edu_program_id in _edu_program_ids(anchor)
    }
    if not profile_ids:
        raise SourceSchemaError(f"Tracked profile for {program.code} was not found")
    selected = [
        competition
        for competition in competitions
        if str(competition.get("eduProgramFormCode") or "") == "1"
        and bool(profile_ids.intersection(_edu_program_ids(competition)))
    ]
    if not selected:
        raise SourceSchemaError(f"No competitions found for tracked profile {program.code}")
    return selected


def extract_competition_cards(
    page_html: str,
    *,
    campaign_id: int,
    base_url: str,
) -> list[CompetitionCard]:
    soup = BeautifulSoup(page_html, "lxml")
    cards: list[CompetitionCard] = []
    seen_ids: set[str] = set()
    for link in soup.find_all("a", href=True):
        href = str(link["href"])
        match = COMPETITION_LINK_RE.search(href)
        if match is None or int(match.group("campaign_id")) != campaign_id:
            continue
        competition_id = match.group("competition_id")
        if competition_id in seen_ids:
            continue
        text = _normalize_text(link.get_text(" ", strip=True))
        card = _competition_card_from_text(
            competition_id=competition_id,
            source_url=urljoin(base_url + "/", href),
            text=text,
        )
        if card is None:
            continue
        cards.append(card)
        seen_ids.add(competition_id)
    return cards


def select_tracked_competition_card(
    cards: list[CompetitionCard],
    program: ProgramConfig,
    funding: Funding,
) -> CompetitionCard:
    places = program.general_places if funding == Funding.BUDGET else program.paid_places
    candidates = [
        card
        for card in cards
        if card.program_code == program.code
        and card.study_form == "full_time"
        and card.funding_type == funding
        and _is_primary_basis(card)
    ]
    exact_place_candidates = [card for card in candidates if card.places == places]
    selected = exact_place_candidates or candidates
    if len(selected) != 1:
        raise SourceSchemaError(
            f"Expected one overview card for {program.code}/{funding.value}, found {len(selected)}"
        )
    return selected[0]


def select_profile_competition_cards(
    cards: list[CompetitionCard],
    program: ProgramConfig,
) -> list[CompetitionCard]:
    return [
        card
        for card in cards
        if card.program_code == program.code and card.study_form == "full_time"
    ]


def competition_code_for_funding(funding: Funding) -> str:
    return BUDGET_COMPETITION_CODE if funding == Funding.BUDGET else PAID_COMPETITION_CODE


def funding_for_competition_payload(payload: dict[str, Any]) -> Funding:
    code = str(payload.get("code") or "")
    return Funding.PAID if code in PAID_COMPETITION_CODES else Funding.BUDGET


def program_info_for_competition_payload(payload: dict[str, Any]) -> tuple[str, str] | None:
    candidates = [str(payload.get("programSetPrintTitle") or "")]
    edu_programs = payload.get("eduPrograms")
    if isinstance(edu_programs, list):
        candidates.extend(
            str(item.get("fullTitleWithoutSubjectIndex") or "")
            for item in edu_programs
            if isinstance(item, dict)
        )

    for candidate in candidates:
        match = PROGRAM_TITLE_RE.match(candidate.strip())
        if match is None:
            continue
        code = match.group("code")
        name = match.group("name").strip(" -")
        return code, name or code
    return None


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


def _edu_program_ids(competition: dict[str, Any]) -> set[str]:
    edu_programs = competition.get("eduPrograms")
    if not isinstance(edu_programs, list):
        return set()
    return {
        str(item["id"])
        for item in edu_programs
        if isinstance(item, dict) and item.get("id") is not None
    }


def _competition_card_from_text(
    *,
    competition_id: str,
    source_url: str,
    text: str,
) -> CompetitionCard | None:
    segments = [segment.strip() for segment in text.split("/") if segment.strip()]
    if not segments:
        return None
    match = PROGRAM_TITLE_RE.match(segments[0])
    if match is None:
        return None
    program_code = match.group("code")
    program_name = match.group("name").strip(" -") or program_code
    study_form = _study_form_from_segments(segments)
    funding_type = Funding.PAID if "договор" in text.casefold() else Funding.BUDGET
    return CompetitionCard(
        competition_id=competition_id,
        source_url=source_url,
        program_code=program_code,
        program_name=program_name,
        study_form=study_form,
        funding_type=funding_type,
        admission_basis=_admission_basis_from_text(text, funding_type),
        places=_extract_labeled_int(text, "Количество мест") or 0,
        applications_count=_extract_labeled_int(text, "Подано заявлений"),
        withdrawn_count=_extract_labeled_int(text, "Из них забрало документы"),
        raw_text=text,
    )


def _study_form_from_segments(segments: list[str]) -> str:
    if len(segments) < 2:
        return "unknown"
    value = segments[1].casefold()
    if value.startswith("очная форма"):
        return "full_time"
    if value.startswith("заочная форма"):
        return "part_time"
    if value.startswith("очно-заочная форма"):
        return "part_time"
    return "unknown"


def _admission_basis_from_text(text: str, funding_type: Funding) -> str:
    lower = text.casefold()
    if funding_type == Funding.PAID and "по договору" in lower:
        return "По договору"
    if "общий конкурс" in lower:
        return "Общий конкурс"
    if "отдельная квота" in lower or "отд.квота" in lower:
        return "Отдельная квота"
    if "особ" in lower:
        return "Особая квота"
    if "без ви" in lower:
        return "Без ВИ по договору" if funding_type == Funding.PAID else "Без ВИ"
    if "цп" in lower or "целевая" in lower:
        return "Целевая квота"
    return "По договору" if funding_type == Funding.PAID else "general"


def _is_primary_basis(card: CompetitionCard) -> bool:
    if card.funding_type == Funding.PAID:
        return card.admission_basis == "По договору"
    return card.admission_basis == "Общий конкурс"


def _extract_labeled_int(text: str, label: str) -> int | None:
    match = re.search(rf"{re.escape(label)}\s*:\s*(\d+)", text)
    if match is None:
        return None
    return _int_or_none(match.group(1))


def _normalize_text(value: str) -> str:
    return " ".join(value.split())


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
