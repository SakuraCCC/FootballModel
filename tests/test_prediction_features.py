from sqlalchemy.orm import Session

from app.services.prediction.features import FeatureBuilder
from tests.prediction_helpers import create_prediction_dataset


def test_feature_builder_uses_persisted_history_and_reports_missing_standings(session: Session) -> None:
    target = create_prediction_dataset(session)

    features = FeatureBuilder(session).build(target.id)

    assert features.home_team.recent_form == ["W", "W", "W"]
    assert features.home_team.recent_goals_for == 2
    assert features.away_team.recent_goals_against == 1
    assert features.league_average_goals is not None
    assert features.input_snapshot_id is not None
    assert features.home_team.league_rank is None
    assert "league_rank" in features.missing_fields
    assert features.data_completeness == "medium"
