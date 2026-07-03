from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Funding(StrEnum):
    BUDGET = "budget"
    PAID = "paid"


class SourceStatus(StrEnum):
    OK = "ok"
    UNAVAILABLE = "unavailable"
    SCHEMA_CHANGED = "schema_changed"


class ApplicantRow(BaseModel):
    anonymous_applicant_id: str | None = None
    position: int | None = None
    total_score: int | None = None
    exam_score_sum: int | None = None
    individual_achievements: int | None = None
    priority: int | None = None
    consent_status: bool | None = None
    original_status: bool | None = None
    application_status: str | None = None
    enrollment_status: str | None = None
    without_exams: bool = False
    quota_type: str | None = None
    higher_priority_status: str | None = None
    source_row_hash: str | None = None

    @property
    def is_active(self) -> bool:
        status = (self.application_status or "").lower()
        enrollment = (self.enrollment_status or "").lower()
        inactive_markers = ("отозв", "исключ", "withdraw", "reject", "зачислен")
        return not any(marker in status or marker in enrollment for marker in inactive_markers)

    @property
    def has_decision_data(self) -> bool:
        return self.priority is not None or self.consent_status is not None or self.original_status is not None


class CompetitionMetadata(BaseModel):
    campaign_id: int | None = None
    competition_id: str | None = None
    program_code: str
    program_name: str
    study_form: str = "full_time"
    funding_type: Funding
    admission_basis: str = "general"
    published_places: int
    applications_count: int | None = None
    withdrawn_count: int | None = None
    general_competition_places: int | None = None
    paid_places: int | None = None
    list_updated_at: datetime | None = None
    source_url: str | None = None
    source_hash: str | None = None


class CompetitionList(BaseModel):
    metadata: CompetitionMetadata
    rows: list[ApplicantRow] = Field(default_factory=list)
    raw: dict[str, Any] | None = None
    source_status: SourceStatus = SourceStatus.OK
    schema_hash: str | None = None


class ProgramBundle(BaseModel):
    program_code: str
    budget: CompetitionList | None = None
    paid: CompetitionList | None = None
