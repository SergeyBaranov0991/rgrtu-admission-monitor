from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class SubjectDiscovery:
    campaign_id: int
    subjects: dict[str, str]
    component_name: str
    livewire_id: str


INITIAL_DATA_RE = re.compile(r'wire:initial-data="([^"]+)"')


async def discover_subjects(
    base_url: str,
    campaign_id: int,
    user_agent: str,
    *,
    verify_ssl: bool = True,
) -> SubjectDiscovery:
    url = f"{base_url.rstrip('/')}/guest/competition-lists/{campaign_id}"
    async with httpx.AsyncClient(
        timeout=30,
        headers={"User-Agent": user_agent},
        verify=verify_ssl,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
    return parse_subjects_from_livewire(response.text)


def parse_subjects_from_livewire(page_html: str) -> SubjectDiscovery:
    for raw in INITIAL_DATA_RE.findall(page_html):
        try:
            data = json.loads(html.unescape(raw))
        except json.JSONDecodeError:
            continue
        fingerprint = data.get("fingerprint", {})
        if fingerprint.get("name") != "competition-lists-common":
            continue
        memo_data = data.get("serverMemo", {}).get("data", {})
        subjects = memo_data.get("subjects", {})
        return SubjectDiscovery(
            campaign_id=int(memo_data.get("campaignId")),
            subjects={str(key): str(value) for key, value in subjects.items()},
            component_name=str(fingerprint["name"]),
            livewire_id=str(fingerprint["id"]),
        )
    raise ValueError("competition-lists-common Livewire component was not found")
