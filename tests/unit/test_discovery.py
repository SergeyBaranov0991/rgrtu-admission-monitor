from app.rgrtu.discovery import parse_subjects_from_livewire


def test_parse_subjects_from_livewire() -> None:
    html = (
        '<div wire:initial-data="{&quot;fingerprint&quot;:{&quot;id&quot;:&quot;abc&quot;,'
        '&quot;name&quot;:&quot;competition-lists-common&quot;},&quot;serverMemo&quot;:{&quot;data&quot;:'
        '{&quot;campaignId&quot;:20,&quot;subjects&quot;:{&quot;1&quot;:&quot;09.03.02 Test&quot;}}}}"></div>'
    )

    discovery = parse_subjects_from_livewire(html)

    assert discovery.campaign_id == 20
    assert discovery.subjects["1"] == "09.03.02 Test"

