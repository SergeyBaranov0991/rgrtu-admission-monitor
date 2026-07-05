from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from pydantic import BaseModel

from app.admission.ranking import RankInterval, effective_rows, passing_score, score_rank_interval
from app.admission.zones import AdmissionZone
from app.rgrtu.base import CompetitionList, SourceStatus


OFFICIAL_LIST_DATE = date(2026, 7, 27)
PRELIMINARY_FORECAST_SPREAD = 7
FINAL_FORECAST_SPREAD = 4
HIGH_CONFIDENCE_THRESHOLD = 0.75
HIGH_CONFIDENCE_SPREAD_REDUCTION = 2
MIN_HIGH_CONFIDENCE_SPREAD = 2
DRAFT_PRELIMINARY_FORECAST_SPREAD = 15
DRAFT_FINAL_FORECAST_SPREAD = 10


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
    target_priority: int | None = None
    ranking_mode: str = "raw"
    relative_rows_count: int | None = None
    relative_excluded_by: str | None = None


@dataclass(frozen=True)
class PassingScoreEstimate:
    has_complete_score_rows: bool
    current_score: int | None
    published_floor: int | None
    forecast_score: tuple[int, int] | None
    draft_forecast_score: tuple[int, int] | None


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
            preliminary=_is_preliminary(today),
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

    preliminary = _is_preliminary(today)
    confidence = _confidence(competition, scored_rows_count, preliminary)
    passing = _passing_score_estimate(
        competition,
        scored_rows_count=scored_rows_count,
        confidence=confidence,
        preliminary=preliminary,
    )
    position_for_zone = raw_interval if passing.has_complete_score_rows else None
    zone = _zone(position_for_zone, places)

    return AdmissionEstimate(
        program_code=metadata.program_code,
        program_name=metadata.program_name,
        funding_type=metadata.funding_type.value,
        admission_basis=metadata.admission_basis,
        places=places,
        target_score=target_score,
        raw_position=_as_tuple(raw_interval),
        effective_position=_as_tuple(effective_interval),
        current_passing_score=passing.current_score,
        forecast_passing_score=passing.forecast_score,
        published_score_floor=passing.published_floor,
        draft_forecast_score=passing.draft_forecast_score,
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
    use_row_position: bool = True,
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
    position = (
        (row.position, row.position)
        if use_row_position and row.position is not None
        else estimate.raw_position
    )
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


def _is_preliminary(today: date) -> bool:
    return today < OFFICIAL_LIST_DATE


def _passing_score_estimate(
    competition: CompetitionList,
    *,
    scored_rows_count: int,
    confidence: float,
    preliminary: bool,
) -> PassingScoreEstimate:
    has_complete_score_rows = scored_rows_count >= competition.metadata.published_places
    score_floor = passing_score(competition.rows, competition.metadata.published_places)
    current_score = score_floor if has_complete_score_rows else None
    return PassingScoreEstimate(
        has_complete_score_rows=has_complete_score_rows,
        current_score=current_score,
        published_floor=None if has_complete_score_rows else score_floor,
        forecast_score=_forecast(current_score, confidence, preliminary),
        draft_forecast_score=(
            None if has_complete_score_rows else _draft_forecast(score_floor, preliminary)
        ),
    )


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
    spread = PRELIMINARY_FORECAST_SPREAD if preliminary else FINAL_FORECAST_SPREAD
    if confidence >= HIGH_CONFIDENCE_THRESHOLD:
        spread = max(MIN_HIGH_CONFIDENCE_SPREAD, spread - HIGH_CONFIDENCE_SPREAD_REDUCTION)
    return (max(0, current_passing - spread), current_passing + spread)


def _draft_forecast(score_floor: int | None, preliminary: bool) -> tuple[int, int] | None:
    if score_floor is None:
        return None
    spread = DRAFT_PRELIMINARY_FORECAST_SPREAD if preliminary else DRAFT_FINAL_FORECAST_SPREAD
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
