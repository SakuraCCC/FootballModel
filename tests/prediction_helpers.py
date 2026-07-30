from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import ActualResult, Competition, DataSource, Match, RawDataSnapshot, Team


def create_prediction_dataset(session: Session) -> Match:
    source = DataSource(
        name="API-Football-v3",
        source_name="API-Football",
        source_type="football_data_api",
        source_tier="secondary",
        api_version="v3",
        reliability_level="reported",
        metadata_={},
    )
    competition = Competition(code="CSL", name="Chinese Super League", region="China", certainty="reported")
    home = Team(canonical_name="Home FC", normalized_name="home fc", certainty="reported")
    away = Team(canonical_name="Away FC", normalized_name="away fc", certainty="reported")
    opponents = [
        Team(canonical_name=f"Opponent {index}", normalized_name=f"opponent {index}", certainty="reported")
        for index in range(1, 7)
    ]
    session.add_all([source, competition, home, away, *opponents])
    session.flush()
    snapshot = RawDataSnapshot(
        data_source_id=source.id,
        provider="API-Football",
        endpoint="fixtures",
        request_time=datetime(2026, 6, 1, tzinfo=UTC),
        retrieved_at=datetime(2026, 6, 1, tzinfo=UTC),
        response_json={"response": []},
    )
    session.add(snapshot)
    fixture_time = datetime(2026, 8, 1, 12, tzinfo=UTC)
    historic_matches = []
    for index in range(3):
        historic_matches.append(
            (home.id, opponents[index].id, fixture_time - timedelta(days=30 - index * 7), 2, 1)
        )
    for index in range(3):
        historic_matches.append(
            (opponents[index + 3].id, away.id, fixture_time - timedelta(days=20 - index * 6), 1, 1)
        )
    for home_id, away_id, kickoff, home_score, away_score in historic_matches:
        match = Match(
            competition_id=competition.id,
            home_team_id=home_id,
            away_team_id=away_id,
            kickoff_at=kickoff,
            status="FT",
            source_id=source.id,
            certainty="reported",
        )
        session.add(match)
        session.flush()
        session.add(
            ActualResult(
                match_id=match.id,
                home_score=home_score,
                away_score=away_score,
                completed_at=kickoff + timedelta(hours=2),
            )
        )
    target = Match(
        competition_id=competition.id,
        home_team_id=home.id,
        away_team_id=away.id,
        kickoff_at=fixture_time,
        status="NS",
        source_id=source.id,
        certainty="reported",
    )
    session.add(target)
    session.commit()
    return target
