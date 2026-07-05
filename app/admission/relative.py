from __future__ import annotations

from dataclasses import dataclass

from app.admission.ranking import score_rank_interval
from app.rgrtu.base import ApplicantRow, CompetitionList


@dataclass(frozen=True)
class CompetitionRef:
    index: int
    label: str


@dataclass(frozen=True)
class Participation:
    competition: CompetitionRef
    row: ApplicantRow


@dataclass(frozen=True)
class RelativeExclusion:
    applicant_id: str
    current: CompetitionRef
    higher: CompetitionRef
    current_priority: int
    higher_priority: int


@dataclass(frozen=True)
class RelativeSelection:
    competitions: list[CompetitionList]
    exclusions: dict[tuple[int, str], RelativeExclusion]


def build_relative_selection(competitions: list[CompetitionList]) -> RelativeSelection:
    participations_by_applicant = _participations_by_applicant(competitions)
    active_ids = _initial_active_ids(competitions)
    exclusions: dict[tuple[int, str], RelativeExclusion] = {}

    for _ in range(_max_iterations(competitions)):
        admitted = _admitted_participations(
            competitions,
            active_ids=active_ids,
            participations_by_applicant=participations_by_applicant,
        )
        next_active_ids, next_exclusions = _next_active_ids(
            competitions,
            admitted_by_applicant=admitted,
        )
        if next_active_ids == active_ids:
            exclusions = next_exclusions
            break
        active_ids = next_active_ids
        exclusions = next_exclusions

    filtered = [
        competition.model_copy(
            update={
                "rows": [
                    row
                    for row in competition.rows
                    if _row_key(row) in active_ids.get(index, set())
                ]
            }
        )
        for index, competition in enumerate(competitions)
    ]
    return RelativeSelection(competitions=filtered, exclusions=exclusions)


def find_row_by_applicant_id(competition: CompetitionList, applicant_id: str) -> ApplicantRow | None:
    rows = [
        row
        for row in competition.rows
        if row.is_active and row.anonymous_applicant_id == applicant_id
    ]
    if not rows:
        return None
    return min(rows, key=lambda row: row.position or 10**9)


def relative_rows_count(competition: CompetitionList) -> int:
    return sum(1 for row in competition.rows if row.is_active)


def _participations_by_applicant(
    competitions: list[CompetitionList],
) -> dict[str, list[Participation]]:
    participations: dict[str, list[Participation]] = {}
    for index, competition in enumerate(competitions):
        ref = _competition_ref(index, competition)
        for row in competition.rows:
            if not row.is_active or not row.anonymous_applicant_id:
                continue
            participations.setdefault(row.anonymous_applicant_id, []).append(
                Participation(competition=ref, row=row)
            )
    return participations


def _initial_active_ids(competitions: list[CompetitionList]) -> dict[int, set[str]]:
    return {
        index: {
            key
            for row in competition.rows
            if row.is_active and (key := _row_key(row)) is not None
        }
        for index, competition in enumerate(competitions)
    }


def _admitted_participations(
    competitions: list[CompetitionList],
    *,
    active_ids: dict[int, set[str]],
    participations_by_applicant: dict[str, list[Participation]],
) -> dict[str, list[Participation]]:
    admitted: dict[str, list[Participation]] = {}
    for index, competition in enumerate(competitions):
        rows = [
            row
            for row in competition.rows
            if _row_key(row) in active_ids.get(index, set())
        ]
        places = competition.metadata.published_places
        if places <= 0:
            continue
        for row in rows:
            applicant_id = row.anonymous_applicant_id
            if not applicant_id or row.priority is None or row.total_score is None:
                continue
            interval = score_rank_interval(rows, row.total_score)
            if interval is None or interval.worst > places:
                continue
            participation = _participation_for(
                participations_by_applicant,
                applicant_id=applicant_id,
                competition_index=index,
            )
            if participation is not None:
                admitted.setdefault(applicant_id, []).append(participation)
    return admitted


def _next_active_ids(
    competitions: list[CompetitionList],
    *,
    admitted_by_applicant: dict[str, list[Participation]],
) -> tuple[dict[int, set[str]], dict[tuple[int, str], RelativeExclusion]]:
    active_ids: dict[int, set[str]] = {}
    exclusions: dict[tuple[int, str], RelativeExclusion] = {}
    for index, competition in enumerate(competitions):
        current_ref = _competition_ref(index, competition)
        selected: set[str] = set()
        for row in competition.rows:
            key = _row_key(row)
            if not row.is_active or key is None:
                continue
            higher = _best_higher_admission(row, admitted_by_applicant.get(key, []))
            if higher is None:
                selected.add(key)
                continue
            exclusions[(index, key)] = RelativeExclusion(
                applicant_id=key,
                current=current_ref,
                higher=higher.competition,
                current_priority=row.priority or 0,
                higher_priority=higher.row.priority or 0,
            )
        active_ids[index] = selected
    return active_ids, exclusions


def _best_higher_admission(
    row: ApplicantRow,
    admitted: list[Participation],
) -> Participation | None:
    if row.priority is None:
        return None
    higher = [
        participation
        for participation in admitted
        if participation.row.priority is not None
        and participation.row.priority < row.priority
    ]
    if not higher:
        return None
    return min(higher, key=lambda participation: participation.row.priority or 10**9)


def _participation_for(
    participations_by_applicant: dict[str, list[Participation]],
    *,
    applicant_id: str,
    competition_index: int,
) -> Participation | None:
    for participation in participations_by_applicant.get(applicant_id, []):
        if participation.competition.index == competition_index:
            return participation
    return None


def _competition_ref(index: int, competition: CompetitionList) -> CompetitionRef:
    metadata = competition.metadata
    funding = "платное" if metadata.funding_type.value == "paid" else "бюджет"
    basis_value = metadata.admission_basis.strip()
    basis = (
        ""
        if not basis_value or basis_value.casefold() in {"general", "общий конкурс", "по договору"}
        else f", {basis_value}"
    )
    return CompetitionRef(
        index=index,
        label=f"{metadata.program_code} {metadata.program_name} - {funding}{basis}",
    )


def _row_key(row: ApplicantRow) -> str | None:
    return row.anonymous_applicant_id


def _max_iterations(competitions: list[CompetitionList]) -> int:
    return max(1, sum(len(competition.rows) for competition in competitions) + 1)
