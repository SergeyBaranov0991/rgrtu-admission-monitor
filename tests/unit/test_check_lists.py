from app.config import Settings
from app.jobs import check_lists


async def test_code_relative_loads_all_full_time_competitions(monkeypatch) -> None:
    calls: list[str] = []

    async def fake_load_all_full_time_competitions(settings: Settings) -> list:
        calls.append("all")
        return []

    async def fake_load_live_competitions(
        settings: Settings,
        *,
        category_scope: str = "general",
    ) -> list:
        calls.append("tracked")
        return []

    monkeypatch.setattr(
        check_lists,
        "load_all_full_time_competitions",
        fake_load_all_full_time_competitions,
    )
    monkeypatch.setattr(check_lists, "load_live_competitions", fake_load_live_competitions)

    await check_lists.estimate_from_live(
        195,
        Settings(),
        entrant_code="1158236",
        relative=True,
    )

    assert calls == ["all"]
