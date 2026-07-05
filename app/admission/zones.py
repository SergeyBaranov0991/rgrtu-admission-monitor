from __future__ import annotations

from enum import StrEnum


class AdmissionZone(StrEnum):
    PASSING = "PASSING"
    BORDERLINE = "BORDERLINE"
    NON_PASSING = "NON_PASSING"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    HIGHER_PRIORITY = "HIGHER_PRIORITY"


ZONE_LABELS: dict[AdmissionZone, str] = {
    AdmissionZone.PASSING: "проходная зона",
    AdmissionZone.BORDERLINE: "пограничная зона",
    AdmissionZone.NON_PASSING: "непроходная зона",
    AdmissionZone.INSUFFICIENT_DATA: "недостаточно данных",
    AdmissionZone.SOURCE_UNAVAILABLE: "источник недоступен",
    AdmissionZone.HIGHER_PRIORITY: "проходит выше по приоритету",
}
