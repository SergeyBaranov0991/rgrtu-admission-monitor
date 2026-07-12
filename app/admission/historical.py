from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


FundingType = Literal["budget", "paid"]

OFFICIAL_GENERAL_HISTORY_URL = (
    "https://rsreu.ru/abitur/bachelor/srednie-i-minimalnye-prokhodnye-bally"
)
OFFICIAL_PAID_ORDER_2025_URLS = (
    "https://rsreu.ru/component/docman/doc_download/20635-prikaz-932-d-ot-28-08-2025-kommertsiya-ochnoe",
    "https://rsreu.ru/component/docman/doc_download/20634-prikaz-933-d-ot-28-08-2025-kommertsiya-ochnoe",
)


@dataclass(frozen=True)
class HistoricalScore:
    year: int
    minimum_score: int
    average_score: int | None = None
    source: str = "official"


@dataclass(frozen=True)
class HistoricalForecast:
    passing_score_range: tuple[int, int]
    average_score_range: tuple[int, int] | None
    years: tuple[int, ...]
    source: str


BUDGET_GENERAL_COMPETITION: dict[str, tuple[HistoricalScore, ...]] = {
    "01.03.02": (
        HistoricalScore(year=2024, minimum_score=211, average_score=225),
        HistoricalScore(year=2025, minimum_score=194, average_score=217),
    ),
    "02.00.00": (
        HistoricalScore(year=2024, minimum_score=214, average_score=230),
        HistoricalScore(year=2025, minimum_score=199, average_score=222),
    ),
    "09.03.01": (
        HistoricalScore(year=2024, minimum_score=208, average_score=223),
        HistoricalScore(year=2025, minimum_score=209, average_score=226),
    ),
    "09.03.02": (
        HistoricalScore(year=2024, minimum_score=207, average_score=214),
        HistoricalScore(year=2025, minimum_score=210, average_score=228),
    ),
    "09.03.03": (
        HistoricalScore(year=2024, minimum_score=234, average_score=240),
        HistoricalScore(year=2025, minimum_score=237, average_score=244),
    ),
    "09.03.04": (
        HistoricalScore(year=2024, minimum_score=248, average_score=263),
        HistoricalScore(year=2025, minimum_score=246, average_score=262),
    ),
    "09.05.01": (
        HistoricalScore(year=2024, minimum_score=206, average_score=225),
        HistoricalScore(year=2025, minimum_score=194, average_score=216),
    ),
    "10.00.00": (
        HistoricalScore(year=2024, minimum_score=214, average_score=224),
        HistoricalScore(year=2025, minimum_score=207, average_score=233),
    ),
    "11.03.01": (
        HistoricalScore(year=2024, minimum_score=151, average_score=181),
        HistoricalScore(year=2025, minimum_score=137, average_score=169),
    ),
    "11.03.02": (
        HistoricalScore(year=2024, minimum_score=163, average_score=187),
        HistoricalScore(year=2025, minimum_score=152, average_score=179),
    ),
    "11.03.03": (
        HistoricalScore(year=2024, minimum_score=166, average_score=194),
        HistoricalScore(year=2025, minimum_score=158, average_score=191),
    ),
    "11.03.04": (
        HistoricalScore(year=2024, minimum_score=157, average_score=190),
        HistoricalScore(year=2025, minimum_score=147, average_score=177),
    ),
    "11.05.01": (
        HistoricalScore(year=2024, minimum_score=154, average_score=182),
        HistoricalScore(year=2025, minimum_score=143, average_score=184),
    ),
    "12.03.01": (
        HistoricalScore(year=2025, minimum_score=123, average_score=161),
    ),
    "12.03.04": (
        HistoricalScore(year=2024, minimum_score=164, average_score=190),
        HistoricalScore(year=2025, minimum_score=176, average_score=191),
    ),
    "12.05.01": (
        HistoricalScore(year=2024, minimum_score=193, average_score=204),
        HistoricalScore(year=2025, minimum_score=164, average_score=197),
    ),
    "13.03.02": (
        HistoricalScore(year=2024, minimum_score=170, average_score=191),
        HistoricalScore(year=2025, minimum_score=177, average_score=205),
    ),
    "15.03.04": (
        HistoricalScore(year=2024, minimum_score=204, average_score=222),
        HistoricalScore(year=2025, minimum_score=199, average_score=219),
    ),
    "15.03.06": (
        HistoricalScore(year=2024, minimum_score=198, average_score=208),
        HistoricalScore(year=2025, minimum_score=173, average_score=205),
    ),
    "18.03.01": (
        HistoricalScore(year=2024, minimum_score=162, average_score=203),
        HistoricalScore(year=2025, minimum_score=130, average_score=200),
    ),
    "27.03.01": (
        HistoricalScore(year=2025, minimum_score=130, average_score=170),
    ),
    "27.03.04": (
        HistoricalScore(year=2024, minimum_score=195, average_score=204),
        HistoricalScore(year=2025, minimum_score=190, average_score=210),
    ),
    "38.03.01": (
        HistoricalScore(year=2024, minimum_score=272, average_score=276),
    ),
}

PAID_CONTRACT_2025: dict[str, tuple[HistoricalScore, ...]] = {
    "01.03.02": (HistoricalScore(year=2025, minimum_score=149, average_score=162),),
    "02.00.00": (HistoricalScore(year=2025, minimum_score=125, average_score=169),),
    "09.03.01": (HistoricalScore(year=2025, minimum_score=125, average_score=168),),
    "09.03.02": (HistoricalScore(year=2025, minimum_score=127, average_score=160),),
    "09.03.03": (HistoricalScore(year=2025, minimum_score=135, average_score=145),),
    "09.03.04": (HistoricalScore(year=2025, minimum_score=125, average_score=166),),
    "10.00.00": (HistoricalScore(year=2025, minimum_score=131, average_score=164),),
    "11.03.01": (HistoricalScore(year=2025, minimum_score=157, average_score=157),),
    "11.03.02": (HistoricalScore(year=2025, minimum_score=125, average_score=151),),
    "12.03.04": (HistoricalScore(year=2025, minimum_score=132, average_score=149),),
    "13.03.02": (HistoricalScore(year=2025, minimum_score=122, average_score=146),),
    "15.03.04": (HistoricalScore(year=2025, minimum_score=141, average_score=165),),
    "15.03.06": (HistoricalScore(year=2025, minimum_score=132, average_score=156),),
    "38.03.01": (HistoricalScore(year=2025, minimum_score=127, average_score=188),),
    "38.03.04": (HistoricalScore(year=2025, minimum_score=127, average_score=172),),
    "38.03.05": (HistoricalScore(year=2025, minimum_score=127, average_score=178),),
}

PROGRAM_CODE_ALIASES = {
    "02.03.01": "02.00.00",
    "02.03.02": "02.00.00",
    "10.05.01": "10.00.00",
    "10.05.03": "10.00.00",
}


def historical_forecast(program_code: str, funding_type: FundingType | str) -> HistoricalForecast | None:
    lookup_code = PROGRAM_CODE_ALIASES.get(program_code, program_code)
    entries = _entries_for(lookup_code, funding_type)
    if not entries:
        return None

    minimum_scores = [entry.minimum_score for entry in entries]
    average_scores = [entry.average_score for entry in entries if entry.average_score is not None]
    return HistoricalForecast(
        passing_score_range=(min(minimum_scores), max(minimum_scores)),
        average_score_range=(
            (min(average_scores), max(average_scores)) if average_scores else None
        ),
        years=tuple(sorted({entry.year for entry in entries})),
        source=_source_for(funding_type),
    )


def historical_prior_note() -> str:
    return (
        "Историческая модель использует официальные минимальные/средние баллы "
        "общего конкурса и приказы о зачислении на коммерцию за прошлые годы."
    )


def _entries_for(program_code: str, funding_type: FundingType | str) -> tuple[HistoricalScore, ...]:
    if funding_type == "paid":
        return PAID_CONTRACT_2025.get(program_code, ())
    return BUDGET_GENERAL_COMPETITION.get(program_code, ())


def _source_for(funding_type: FundingType | str) -> str:
    if funding_type == "paid":
        return "official_paid_orders"
    return "official_general_competition"
