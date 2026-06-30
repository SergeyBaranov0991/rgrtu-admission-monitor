from __future__ import annotations

import hashlib
import json
from typing import Any

from bs4 import BeautifulSoup

from app.rgrtu.base import ApplicantRow, CompetitionList, CompetitionMetadata, Funding


def parse_fixture_payload(payload: dict[str, Any]) -> CompetitionList:
    metadata = CompetitionMetadata(**payload["metadata"])
    rows = [ApplicantRow(**row) for row in payload.get("rows", [])]
    schema_hash = _schema_hash(payload)
    return CompetitionList(metadata=metadata, rows=rows, raw=payload, schema_hash=schema_hash)


def parse_fixture_file(path: str) -> list[CompetitionList]:
    with open(path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if isinstance(payload, dict) and "competitions" in payload:
        return [parse_fixture_payload(item) for item in payload["competitions"]]
    if isinstance(payload, dict):
        return [parse_fixture_payload(payload)]
    raise ValueError("Unsupported fixture format")


def parse_competition_table_html(
    html: str,
    *,
    program_code: str,
    program_name: str,
    funding_type: Funding,
    places: int,
    source_url: str,
) -> CompetitionList:
    soup = BeautifulSoup(html, "lxml")
    rows: list[ApplicantRow] = []

    for tr in soup.select("table tr"):
        cells = [cell.get_text(" ", strip=True) for cell in tr.find_all(["td", "th"])]
        if len(cells) < 2:
            continue
        position = _int_or_none(cells[0])
        score_candidates = [
            score
            for score in (_int_or_none(cell) for cell in cells[1:])
            if score is not None and 0 <= score <= 310
        ]
        total_score = max(score_candidates) if score_candidates else None
        if position is None or total_score is None:
            continue
        rows.append(
            ApplicantRow(
                position=position,
                total_score=total_score,
                anonymous_applicant_id=hashlib.sha256(" ".join(cells).encode()).hexdigest()[:16],
                source_row_hash=hashlib.sha256("|".join(cells).encode()).hexdigest(),
            )
        )

    metadata = CompetitionMetadata(
        program_code=program_code,
        program_name=program_name,
        funding_type=funding_type,
        published_places=places,
        source_url=source_url,
        source_hash=hashlib.sha256(html.encode("utf-8")).hexdigest(),
    )
    return CompetitionList(metadata=metadata, rows=rows, schema_hash=_schema_hash({"table": True}))


def _int_or_none(value: str) -> int | None:
    digits = "".join(ch for ch in value if ch.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def _schema_hash(payload: dict[str, Any]) -> str:
    def walk(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {key: walk(value) for key, value in sorted(obj.items())}
        if isinstance(obj, list):
            if not obj:
                return []
            return [walk(obj[0])]
        return type(obj).__name__

    return hashlib.sha256(json.dumps(walk(payload), sort_keys=True).encode("utf-8")).hexdigest()
