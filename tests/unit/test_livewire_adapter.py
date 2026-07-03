import pytest

from app.config import PROGRAMS
from app.admission.estimator import estimate_competition
from app.rgrtu.base import Funding
from app.rgrtu.livewire_adapter import (
    SourceSchemaError,
    build_empty_competition,
    build_filter_updates,
    extract_livewire_component,
    extract_livewire_response_html,
    extract_livewire_token,
    select_profile_competitions,
    select_tracked_competition,
)
from app.rgrtu.parser import parse_competition_payload, parse_competition_table_html


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


def test_select_tracked_competition_uses_places_to_disambiguate_profiles() -> None:
    program = next(program for program in PROGRAMS if program.code == "09.03.02")
    competitions = [
        {
            "id": "wrong-profile",
            "programSetPrintTitle": "09.03.02 Информационные системы и технологии",
            "code": "04",
            "eduProgramFormCode": "1",
            "plan": 7,
        },
        {
            "id": "tracked-profile",
            "programSetPrintTitle": "09.03.02 Информационные системы и технологии",
            "code": "04",
            "eduProgramFormCode": "1",
            "plan": 19,
        },
    ]

    selected = select_tracked_competition(competitions, program, Funding.BUDGET)

    assert selected["id"] == "tracked-profile"


def test_select_profile_competitions_uses_tracked_profile_id() -> None:
    program = next(program for program in PROGRAMS if program.code == "09.03.02")
    competitions = [
        {
            "id": "other-general",
            "programSetPrintTitle": "09.03.02 Информационные системы и технологии",
            "code": "04",
            "eduProgramFormCode": "1",
            "plan": 7,
            "eduPrograms": [{"id": "other-profile"}],
        },
        {
            "id": "tracked-quota",
            "programSetPrintTitle": "09.03.02 Информационные системы и технологии",
            "code": "07",
            "eduProgramFormCode": "1",
            "plan": 4,
            "eduPrograms": [{"id": "tracked-profile"}],
        },
        {
            "id": "tracked-general",
            "programSetPrintTitle": "09.03.02 Информационные системы и технологии",
            "code": "04",
            "eduProgramFormCode": "1",
            "plan": 19,
            "eduPrograms": [{"id": "tracked-profile"}],
        },
        {
            "id": "tracked-paid",
            "programSetPrintTitle": "09.03.02 Информационные системы и технологии",
            "code": "06",
            "eduProgramFormCode": "1",
            "plan": 15,
            "eduPrograms": [{"id": "tracked-profile"}],
        },
    ]

    selected = select_profile_competitions(competitions, program)

    assert [competition["id"] for competition in selected] == [
        "tracked-quota",
        "tracked-general",
        "tracked-paid",
    ]


def test_competition_payload_keeps_official_applications_count() -> None:
    payload = {
        "id": "1863247416534381847",
        "code": "04",
        "type": "Общий конкурс",
        "programSetPrintTitle": "01.03.02 Прикладная математика и информатика",
        "plan": 10,
        "submitted": 141,
        "taken": 0,
        "entrants": [
            {
                "firstRating": 1,
                "superServiceCode": "1043871",
                "name": "Не сохраняется",
                "email": "hidden@example.test",
                "snils": "000-000-000 00",
                "finalMark": "276",
                "entranceMark": "276",
                "achievementMark": "0",
                "printPriority": 5,
                "isAccepted": False,
                "isOriginalIn": False,
                "status": "Участвует в конкурсе",
            }
        ],
    }

    competition = parse_competition_payload(
        payload,
        program_code="01.03.02",
        program_name="Прикладная математика и информатика",
        funding_type=Funding.BUDGET,
        places=10,
        source_url="https://postupai.rsreu.ru/guest/competition-lists/20/1863247416534381847",
        campaign_id=20,
    )
    estimate = estimate_competition(competition, 195)

    assert competition.metadata.applications_count == 141
    assert len(competition.rows) == 1
    assert estimate.rows_count == 141
    assert competition.rows[0].anonymous_applicant_id == "1043871"
    assert competition.rows[0].total_score == 276
    assert "hidden@example.test" not in str(competition.raw)
    assert "000-000-000" not in str(competition.raw)


def test_build_empty_competition_keeps_application_count_zero() -> None:
    competition = build_empty_competition(
        program=PROGRAMS[0],
        funding=Funding.BUDGET,
        campaign_id=20,
        source_url="https://postupai.rsreu.ru/guest/competition-lists/20",
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
        source_url="https://postupai.rsreu.ru/guest/competition-lists/20",
    )

    assert competition.rows[0].position == 1
    assert competition.rows[0].total_score == 195
