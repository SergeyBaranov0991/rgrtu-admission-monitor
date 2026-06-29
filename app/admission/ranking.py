from __future__ import annotations

from dataclasses import dataclass

from app.rgrtu.base import ApplicantRow


@dataclass(frozen=True)
class RankInterval:
    best: int
    worst: int

    def crosses(self, boundary: int) -> bool:
        return self.best <= boundary <= self.worst


def score_rank_interval(rows: list[ApplicantRow], target_score: int) -> RankInterval | None:
    scores = [row.total_score for row in rows if row.total_score is not None and row.is_active]
    if not scores:
        return None
    higher = sum(1 for score in scores if score > target_score)
    equal = sum(1 for score in scores if score == target_score)
    return RankInterval(best=higher + 1, worst=higher + equal + 1)


def passing_score(rows: list[ApplicantRow], places: int) -> int | None:
    if places <= 0:
        return None
    scores = sorted(
        (row.total_score for row in rows if row.total_score is not None and row.is_active),
        reverse=True,
    )
    if not scores:
        return None
    if len(scores) < places:
        return scores[-1]
    return scores[places - 1]


def effective_rows(rows: list[ApplicantRow]) -> list[ApplicantRow]:
    if not any(row.has_decision_data for row in rows):
        return [row for row in rows if row.is_active]

    selected: list[ApplicantRow] = []
    for row in rows:
        if not row.is_active:
            continue
        if row.consent_status is True or row.original_status is True:
            selected.append(row)
            continue
        if row.priority is not None and row.priority <= 2:
            selected.append(row)
    return selected

