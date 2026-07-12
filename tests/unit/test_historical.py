from app.admission.historical import historical_forecast


def test_historical_forecast_uses_official_budget_range() -> None:
    forecast = historical_forecast("09.03.02", "budget")

    assert forecast is not None
    assert forecast.passing_score_range == (207, 210)
    assert forecast.average_score_range == (214, 228)
    assert forecast.years == (2024, 2025)
    assert forecast.source == "official_general_competition"


def test_historical_forecast_uses_paid_contract_orders() -> None:
    forecast = historical_forecast("09.03.03", "paid")

    assert forecast is not None
    assert forecast.passing_score_range == (135, 135)
    assert forecast.average_score_range == (145, 145)
    assert forecast.years == (2025,)
    assert forecast.source == "official_paid_orders"


def test_historical_forecast_maps_program_groups() -> None:
    forecast = historical_forecast("02.03.02", "budget")

    assert forecast is not None
    assert forecast.passing_score_range == (199, 214)
