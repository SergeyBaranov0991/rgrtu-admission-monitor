import pytest

from app.config import PROGRAMS
from app.rgrtu.base import Funding
from app.rgrtu.livewire_adapter import (
    SourceSchemaError,
    build_empty_competition,
    build_filter_updates,
    extract_livewire_component,
    extract_livewire_response_html,
    extract_livewire_token,
)
from app.rgrtu.parser import parse_competition_table_html


def test_extract_livewire_initial_state() -> None:
    html = (
        "<script>window.livewire_token = 'token-123';</script>"
        '<div wire:initial-data="{&quot;fingerprint&quot;:{&quot;id&quot;:&quot;abc&quot;,'
        '&quot;name&quot;:&quot;competition-lists-common&quot;},&quot;serverMemo&quot;:{&quot;data&quot;:'
        '{&quot;campaignId&quot;:20}}}"></div>'
    )

    assert extract_livewire_token(html) == "token-123"
    component = extract_livewire_component(html)

    assert component["fingerprint"]["id"] == "abc"
    assert component["serverMemo"]["data"]["campaignId"] == 20


def test_extract_livewire_token_reports_schema_error() -> None:
    with pytest.raises(SourceSchemaError):
        extract_livewire_token("<html></html>")


def test_extract_livewire_response_html_reports_schema_error() -> None:
    with pytest.raises(SourceSchemaError):
        extract_livewire_response_html({"effects": {}})


def test_build_filter_updates_uses_public_ui_checkbox_values() -> None:
    budget_updates = build_filter_updates("subject-id", Funding.BUDGET)
    paid_updates = build_filter_updates("subject-id", Funding.PAID)

    assert budget_updates[0]["payload"]["params"] == ["subject", "subject-id"]
    assert budget_updates[1]["payload"]["name"] == "eduProgramForms.0.checked"
    assert budget_updates[1]["payload"]["value"] == "2"
    assert budget_updates[2]["payload"]["name"] == "competitionTypes.3.checked"
    assert paid_updates[2]["payload"]["name"] == "competitionTypes.4.checked"


def test_build_empty_competition_keeps_application_count_zero() -> None:
    competition = build_empty_competition(
        program=PROGRAMS[0],
        funding=Funding.BUDGET,
        campaign_id=20,
        source_url="https://postupai.rsreu.ru/guest/entrant-lists/20",
    )

    assert competition.metadata.campaign_id == 20
    assert competition.metadata.program_code == PROGRAMS[0].code
    assert competition.metadata.published_places == PROGRAMS[0].general_places
    assert competition.rows == []


def test_table_parser_does_not_use_position_as_score() -> None:
    competition = parse_competition_table_html(
        "<table><tr><td>1</td><td>anon-1</td><td>195</td></tr></table>",
        program_code=PROGRAMS[0].code,
        program_name=PROGRAMS[0].name,
        funding_type=Funding.BUDGET,
        places=PROGRAMS[0].general_places,
        source_url="https://postupai.rsreu.ru/guest/entrant-lists/20",
    )

    assert competition.rows[0].position == 1
    assert competition.rows[0].total_score == 195
