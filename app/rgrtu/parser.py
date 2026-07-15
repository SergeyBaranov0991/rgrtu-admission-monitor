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


def parse_competition_payload(
    payload: dict[str, Any],
    *,
    program_code: str,
    program_name: str,
    funding_type: Funding,
    places: int,
    source_url: str,
    campaign_id: int | None = None,
) -> CompetitionList:
    rows = [
        _parse_entrant_payload(entrant)
        for entrant in _iter_entrant_payloads(payload.get("entrants"))
        if isinstance(entrant, dict)
    ]
    applications_count = _int_or_none(payload.get("submitted"))
    withdrawn_count = _int_or_none(payload.get("taken"))
    competition_id = _string_or_none(payload.get("id"))
    raw = {
        "competition_id": competition_id,
        "competition_code": _string_or_none(payload.get("code")),
        "competition_type": _string_or_none(payload.get("type")),
        "program_title": _string_or_none(payload.get("programSetPrintTitle")),
        "submitted": applications_count,
        "taken": withdrawn_count,
        "entrants_count": len(rows),
    }
    source_fingerprint = {
        "metadata": raw,
        "row_hashes": [row.source_row_hash for row in rows],
    }
    metadata = CompetitionMetadata(
        campaign_id=campaign_id,
        competition_id=competition_id,
        program_code=program_code,
        program_name=program_name,
        funding_type=funding_type,
        admission_basis=_string_or_none(payload.get("type")) or "general",
        published_places=_int_or_none(payload.get("plan")) or places,
        applications_count=applications_count,
        withdrawn_count=withdrawn_count,
        source_url=source_url,
        source_hash=_hash_json(source_fingerprint),
    )
    return CompetitionList(
        metadata=metadata,
        rows=rows,
        raw=raw,
        schema_hash=_schema_hash(payload),
    )


def parse_competition_table_html(
    html: str,
    *,
    program_code: str,
    program_name: str,
    funding_type: Funding,
    places: int,
    source_url: str,
    campaign_id: int | None = None,
    competition_id: str | None = None,
    admission_basis: str = "general",
    applications_count: int | None = None,
    withdrawn_count: int | None = None,
) -> CompetitionList:
    soup = BeautifulSoup(html, "lxml")
    rows: list[ApplicantRow] = []

    for tr in soup.select("table tr"):
        cells = [cell.get_text(" ", strip=True) for cell in tr.find_all(["td", "th"], recursive=False)]
        if len(cells) < 2:
            continue
        position = _first_int_or_none(cells[0])
        applicant_id = _string_or_none(cells[1]) if len(cells) >= 3 else None
        priority = _int_or_none(cells[3]) if len(cells) >= 4 else None
        consent_status = _bool_or_none(cells[5]) if len(cells) >= 6 else None
        application_status = _string_or_none(cells[6]) if len(cells) >= 7 else None
        higher_priority_status = _dash_to_none(cells[7]) if len(cells) >= 8 else None
        original_status = _bool_or_none(cells[8]) if len(cells) >= 9 else None
        individual_achievements = _int_or_none(cells[9]) if len(cells) >= 10 else None
        total_score = (
            _int_or_none(cells[10])
            if len(cells) >= 11
            else _int_or_none(cells[2]) if len(cells) >= 3 else None
        )
        exam_score_sum = _int_or_none(cells[2]) if len(cells) >= 3 else total_score
        if position is None or total_score is None:
            continue
        rows.append(
            ApplicantRow(
                position=position,
                total_score=total_score,
                anonymous_applicant_id=applicant_id
                if applicant_id and applicant_id.isdigit()
                else hashlib.sha256(" ".join(cells).encode()).hexdigest()[:16],
                exam_score_sum=exam_score_sum,
                individual_achievements=individual_achievements,
                priority=priority,
                consent_status=consent_status,
                original_status=original_status,
                application_status=application_status,
                higher_priority_status=higher_priority_status,
                source_row_hash=hashlib.sha256("|".join(cells).encode()).hexdigest(),
            )
        )

    metadata = CompetitionMetadata(
        campaign_id=campaign_id,
        competition_id=competition_id,
        program_code=program_code,
        program_name=program_name,
        funding_type=funding_type,
        admission_basis=admission_basis,
        published_places=places,
        applications_count=applications_count,
        withdrawn_count=withdrawn_count,
        source_url=source_url,
        source_hash=hashlib.sha256(html.encode("utf-8")).hexdigest(),
    )
    return CompetitionList(metadata=metadata, rows=rows, schema_hash=_schema_hash({"table": True}))


def _iter_entrant_payloads(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return [item for item in value.values() if isinstance(item, dict)]
    if not isinstance(value, list):
        return []

    entrants: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        nested = item.get("entrants")
        if isinstance(nested, dict):
            entrants.extend(row for row in nested.values() if isinstance(row, dict))
            continue
        entrants.append(item)
    return entrants


def _parse_entrant_payload(payload: dict[str, Any]) -> ApplicantRow:
    position = _int_or_none(payload.get("firstRating")) or _int_or_none(payload.get("position"))
    total_score = _int_or_none(payload.get("finalMark"))
    exam_score_sum = _int_or_none(payload.get("entranceMark")) or _sum_marks(payload.get("marks"))
    individual_achievements = _int_or_none(payload.get("achievementMark"))
    priority = _int_or_none(payload.get("printPriority")) or _int_or_none(payload.get("priority"))
    applicant_id = _string_or_none(payload.get("superServiceCode"))
    sanitized = {
        "id": applicant_id,
        "position": position,
        "total_score": total_score,
        "exam_score_sum": exam_score_sum,
        "individual_achievements": individual_achievements,
        "priority": priority,
        "consent_status": _bool_or_none(payload.get("isAccepted")),
        "original_status": _bool_or_none(payload.get("isOriginalIn")),
        "application_status": _string_or_none(payload.get("status")),
        "without_exams": bool(payload.get("noExam")),
    }
    return ApplicantRow(
        anonymous_applicant_id=applicant_id or _hash_json(sanitized)[:16],
        position=position,
        total_score=total_score,
        exam_score_sum=exam_score_sum,
        individual_achievements=individual_achievements,
        priority=priority,
        consent_status=sanitized["consent_status"],
        original_status=sanitized["original_status"],
        application_status=sanitized["application_status"],
        without_exams=sanitized["without_exams"],
        quota_type=_string_or_none(payload.get("preferenceCategory")),
        higher_priority_status=_string_or_none(payload.get("VpRecommendedNoneAgree")),
        source_row_hash=_hash_json(sanitized),
    )


def _sum_marks(value: Any) -> int | None:
    if not isinstance(value, dict):
        return None
    marks = [_int_or_none(mark) for mark in value.values()]
    numeric_marks = [mark for mark in marks if mark is not None]
    if not numeric_marks:
        return None
    return sum(numeric_marks)


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


def _first_int_or_none(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    digits = ""
    for char in str(value):
        if char.isdigit():
            digits += char
            continue
        if digits:
            break
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def _bool_or_none(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"да", "true", "1", "yes"}:
        return True
    if text in {"нет", "false", "0", "no"}:
        return False
    return None


def _dash_to_none(value: Any) -> str | None:
    text = _string_or_none(value)
    if text in {None, "-", "—", "–"}:
        return None
    return text


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _hash_json(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


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
