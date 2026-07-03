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
    admission_basis: str = "general"
    places: int
    target_score: int
    raw_position: tuple[int, int] | None
    effective_position: tuple[int, int] | None
    current_passing_score: int | None
    forecast_passing_score: tuple[int, int] | None
    published_score_floor: int | None = None
    draft_forecast_score: tuple[int, int] | None = None
    zone: AdmissionZone
    confidence: float
    preliminary: bool
    source_url: str | None = None
    source_status: SourceStatus = SourceStatus.OK
    source_error: str | None = None
    rows_count: int
    scored_rows_count: int | None = None
    target_entrant_code: str | None = None
    target_found: bool | None = None


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
        rows_count = _applications_count(competition)
        return AdmissionEstimate(
            program_code=metadata.program_code,
            program_name=metadata.program_name,
            funding_type=metadata.funding_type.value,
            admission_basis=metadata.admission_basis,
            places=places,
            target_score=target_score,
            raw_position=None,
            effective_position=None,
            current_passing_score=None,
            forecast_passing_score=None,
            published_score_floor=None,
            draft_forecast_score=None,
            zone=AdmissionZone.SOURCE_UNAVAILABLE,
            confidence=0.0,
            preliminary=True,
            source_url=metadata.source_url,
            source_status=competition.source_status,
            source_error=_source_error(competition),
            rows_count=rows_count,
            scored_rows_count=None,
        )

    rows_count = _applications_count(competition)
    scored_rows_count = _scored_rows_count(competition)
    raw_interval = score_rank_interval(competition.rows, target_score)
    effective = effective_rows(competition.rows)
    effective_interval = score_rank_interval(effective, target_score)
    has_complete_score_rows = scored_rows_count >= places
    score_floor = passing_score(competition.rows, places)
    current_passing = score_floor if has_complete_score_rows else None

    preliminary = today < date(2026, 7, 27)
    confidence = _confidence(competition, scored_rows_count, preliminary)
    position_for_zone = raw_interval if has_complete_score_rows else None
    zone = _zone(position_for_zone, places)
    forecast = _forecast(current_passing, confidence, preliminary)
    draft_forecast = _draft_forecast(score_floor, preliminary) if not has_complete_score_rows else None

    return AdmissionEstimate(
        program_code=metadata.program_code,
        program_name=metadata.program_name,
        funding_type=metadata.funding_type.value,
        admission_basis=metadata.admission_basis,
        places=places,
        target_score=target_score,
        raw_position=_as_tuple(raw_interval),
        effective_position=_as_tuple(effective_interval),
        current_passing_score=current_passing,
        forecast_passing_score=forecast,
        published_score_floor=score_floor if not has_complete_score_rows else None,
        draft_forecast_score=draft_forecast,
        zone=zone,
        confidence=confidence,
        preliminary=preliminary,
        source_url=metadata.source_url,
        source_status=competition.source_status,
        source_error=_source_error(competition),
        rows_count=rows_count,
        scored_rows_count=scored_rows_count,
    )


def estimate_competition_by_code(
    competition: CompetitionList,
    entrant_code: str,
    *,
    fallback_score: int,
    today: date | None = None,
) -> AdmissionEstimate:
    rows = [row for row in competition.rows if row.anonymous_applicant_id == entrant_code and row.is_active]
    if not rows:
        estimate = estimate_competition(competition, fallback_score, today=today)
        return estimate.model_copy(
            update={
                "raw_position": None,
                "effective_position": None,
                "forecast_passing_score": None,
                "zone": (
                    AdmissionZone.SOURCE_UNAVAILABLE
                    if competition.source_status != SourceStatus.OK
                    else AdmissionZone.INSUFFICIENT_DATA
                ),
                "target_entrant_code": entrant_code,
                "target_found": False if competition.source_status == SourceStatus.OK else None,
            }
        )

    row = min(rows, key=lambda item: item.position or 10**9)
    target_score = row.total_score if row.total_score is not None else fallback_score
    estimate = estimate_competition(competition, target_score, today=today)
    position = (row.position, row.position) if row.position is not None else estimate.raw_position
    zone = estimate.zone
    if position is not None and estimate.scored_rows_count is not None:
        if estimate.scored_rows_count >= estimate.places:
            zone = _zone(_rank_interval(position), estimate.places)
        else:
            zone = AdmissionZone.INSUFFICIENT_DATA
    return estimate.model_copy(
        update={
            "target_score": target_score,
            "raw_position": position,
            "target_entrant_code": entrant_code,
            "target_found": True,
            "zone": zone,
        }
    )


def _as_tuple(interval: RankInterval | None) -> tuple[int, int] | None:
    if interval is None:
        return None
    return (interval.best, interval.worst)


def _rank_interval(value: tuple[int, int]) -> RankInterval:
    return RankInterval(best=value[0], worst=value[1])


def _zone(interval: RankInterval | None, places: int) -> AdmissionZone:
    if places <= 0 or interval is None:
        return AdmissionZone.INSUFFICIENT_DATA
    if interval.worst <= places:
        return AdmissionZone.PASSING
    if interval.best <= places or interval.best <= places + 3:
        return AdmissionZone.BORDERLINE
    return AdmissionZone.NON_PASSING


def _confidence(competition: CompetitionList, scored_rows_count: int, preliminary: bool) -> float:
    if not competition.rows:
        return 0.2
    if scored_rows_count < competition.metadata.published_places:
        base = 0.32
        if preliminary:
            base -= 0.12
        return max(0.1, round(base, 2))

    has_decision_data = any(row.has_decision_data for row in competition.rows)
    base = 0.78 if has_decision_data else 0.56
    applications_count = competition.metadata.applications_count
    if applications_count is not None and scored_rows_count < applications_count:
        base -= 0.1
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


def _draft_forecast(score_floor: int | None, preliminary: bool) -> tuple[int, int] | None:
    if score_floor is None:
        return None
    spread = 15 if preliminary else 10
    return (max(0, score_floor - spread), score_floor + spread)


def _source_error(competition: CompetitionList) -> str | None:
    raw = competition.raw or {}
    error = raw.get("error")
    if error is None:
        return None
    return str(error)


def _applications_count(competition: CompetitionList) -> int:
    if competition.metadata.applications_count is not None:
        return competition.metadata.applications_count
    return len(competition.rows)


def _scored_rows_count(competition: CompetitionList) -> int:
    return sum(
        1
        for row in competition.rows
        if row.total_score is not None and row.is_active
    )
