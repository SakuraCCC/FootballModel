from app.services.normalization import normalize_match
from app.services.quality import assess_match_completeness


def test_missing_injuries_yields_medium_quality_when_core_match_fields_exist() -> None:
    match = normalize_match(
        {
            "fixture": {"id": 10, "date": "2026-08-01T12:00:00+00:00", "status": {"short": "NS"}},
            "teams": {"home": {"id": 1, "name": "Team A"}, "away": {"id": 2, "name": "Team B"}},
        }
    )

    quality = assess_match_completeness(match)

    assert quality.match_time_present is True
    assert quality.teams_present is True
    assert quality.injuries_missing is True
    assert quality.level == "medium"


def test_missing_core_field_yields_low_quality() -> None:
    match = normalize_match(
        {"fixture": {"id": 10, "status": {}}, "teams": {"home": {}, "away": {}}}
    )

    assert assess_match_completeness(match, injuries=[]).level == "low"
