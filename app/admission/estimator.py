from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from app.admission.ranking import RankInterval, effective_rows, passing_score, score_rank_interval
from app.admission.zones import AdmissionZone
from app.rgrtu.base import CompetitionList, SourceStatus


class AdmissionEstimate(BaseModel):
    program_code: str
    program_name: str
    funding_type: str
    places: int
    target_score: int
    raw_position: tuple[int, int] | None
    effective_position: tuple[int, int] | None
    current_passing_score: int | None
    forecast_passing_score: tuple[int, int] | None
    zone: AdmissionZone
    confidence: float
    preliminary: bool
    source_url: str | None = None
    source_status: SourceStatus = SourceStatus.OK
    source_error: str | None = None
    rows_count: int


def estimate_competition(
    competition: CompetitionList,
    target_score: int,
    *,
    today: date | None = None,
) -> AdmissionEstimate:
    today = today or date.today()
    metadata = competition.metadata
    places = metadata.published_places

    if competition.source_status != SourceStatus.OK:
        return AdmissionEstimate(
            program_code=metadata.program_code,
            program_name=metadata.program_name,
            funding_type=metadata.funding_type.value,
            places=places,
            target_score=target_score,
            raw_position=None,
            effective_position=None,
            current_passing_score=None,
            forecast_passing_score=None,
            zone=AdmissionZone.SOURCE_UNAVAILABLE,
            confidence=0.0,
            preliminary=True,
            source_url=metadata.source_url,
            source_status=competition.source_status,
            source_error=_source_error(competition),
            rows_count=len(competition.rows),
        )

    raw_interval = score_rank_interval(competition.rows, target_score)
    effective = effective_rows(competition.rows)
    effective_interval = score_rank_interval(effective, target_score)
    current_passing = passing_score(effective or competition.rows, places)

    preliminary = today < date(2026, 7, 27)
    confidence = _confidence(competition, effective, preliminary)
    position_for_zone = effective_interval or raw_interval
    zone = _zone(position_for_zone, places)
    forecast = _forecast(current_passing, confidence, preliminary)

    return AdmissionEstimate(
        program_code=metadata.program_code,
        program_name=metadata.program_name,
        funding_type=metadata.funding_type.value,
        places=places,
        target_score=target_score,
        raw_position=_as_tuple(raw_interval),
        effective_position=_as_tuple(effective_interval),
        current_passing_score=current_passing,
        forecast_passing_score=forecast,
        zone=zone,
        confidence=confidence,
        preliminary=preliminary,
        source_url=metadata.source_url,
        source_status=competition.source_status,
        source_error=_source_error(competition),
        rows_count=len(competition.rows),
    )


def _as_tuple(interval: RankInterval | None) -> tuple[int, int] | None:
    if interval is None:
        return None
    return (interval.best, interval.worst)


def _zone(interval: RankInterval | None, places: int) -> AdmissionZone:
    if places <= 0 or interval is None:
        return AdmissionZone.INSUFFICIENT_DATA
    if interval.worst <= places:
        return AdmissionZone.PASSING
    if interval.best <= places or interval.best <= places + 3:
        return AdmissionZone.BORDERLINE
    return AdmissionZone.NON_PASSING


def _confidence(competition: CompetitionList, effective: list, preliminary: bool) -> float:
    if not competition.rows:
        return 0.2
    has_decision_data = any(row.has_decision_data for row in competition.rows)
    base = 0.78 if has_decision_data else 0.56
    if len(effective) < competition.metadata.published_places:
        base -= 0.08
    if preliminary:
        base -= 0.12
    return max(0.1, min(0.95, round(base, 2)))


def _forecast(current_passing: int | None, confidence: float, preliminary: bool) -> tuple[int, int] | None:
    if current_passing is None:
        return None
    spread = 7 if preliminary else 4
    if confidence >= 0.75:
        spread = max(2, spread - 2)
    return (max(0, current_passing - spread), current_passing + spread)


def _source_error(competition: CompetitionList) -> str | None:
    raw = competition.raw or {}
    error = raw.get("error")
    if error is None:
        return None
    return str(error)
