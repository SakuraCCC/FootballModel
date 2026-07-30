from sqlalchemy.orm import Session

from app.services.prediction.features import FeatureBuilder
from app.services.prediction.models import EloModel
from tests.prediction_helpers import create_prediction_dataset


def test_elo_uses_chronological_persisted_results(session: Session) -> None:
    target = create_prediction_dataset(session)

    result = EloModel().predict(FeatureBuilder(session).build(target.id))

    assert result.model_status == "available"
    assert result.strength_difference is not None
    assert result.home_advantage == 65
    assert result.win_probability_adjustment is not None
