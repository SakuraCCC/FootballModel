from app.services.normalization import (
    normalize_competition,
    normalize_match,
    normalize_player,
    normalize_team,
)


def test_team_aliases_normalize_to_one_canonical_name() -> None:
    psg = normalize_team({"team": {"id": 85, "name": "PSG"}})
    paris_sg = normalize_team({"team": {"id": 85, "name": "Paris SG"}})

    assert psg.canonical_name == "Paris Saint-Germain"
    assert paris_sg.canonical_name == "Paris Saint-Germain"
    assert psg.normalized_name == paris_sg.normalized_name


def test_competition_player_and_match_normalization_preserve_missing_values() -> None:
    competition = normalize_competition(
        {"league": {"id": 169, "name": "Super League"}, "country": {"name": "China"}}
    )
    player = normalize_player({"player": {"id": 7, "name": "A. Player"}})
    match = normalize_match(
        {
            "fixture": {"id": 10, "date": "2026-08-01T12:00:00+00:00", "status": {"short": "NS"}},
            "league": {"round": "Regular Season"},
            "teams": {"home": {"id": 1, "name": "PSG"}, "away": {"id": 2, "name": "Team B"}},
        }
    )

    assert competition.code == "CSL"
    assert competition.external_id == 169
    assert player.normalized_name == "a player"
    assert match.external_id == "10"
    assert match.home_team.canonical_name == "Paris Saint-Germain"
    assert match.kickoff_at is not None
    assert match.status == "NS"
