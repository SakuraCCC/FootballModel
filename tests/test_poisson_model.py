from sqlalchemy.orm import Session

from app.services.prediction.features import FeatureBuilder
from app.services.prediction.models import DixonColesModel, PoissonModel
from tests.prediction_helpers import create_prediction_dataset


def test_poisson_and_dixon_coles_return_normalized_score_probabilities(session: Session) -> None:
    target = create_prediction_dataset(session)
    features = FeatureBuilder(session).build(target.id)

    poisson = PoissonModel().predict(features)
    dixon_coles = DixonColesModel().predict(features)

    assert poisson.model_status == "available"
    assert dixon_coles.model_status == "available"
    assert abs(sum(item.probability for item in poisson.score_probabilities) - 1) < 0.000_001
    assert abs(sum(item.probability for item in dixon_coles.score_probabilities) - 1) < 0.000_001
    assert len(poisson.top_scores()) == 10


def test_poisson_reports_not_available_without_history(session: Session) -> None:
    from app.models import Competition, Match, Team

    competition = Competition(code="MLS", name="Major League Soccer", region="USA")
    home = Team(canonical_name="Home", normalized_name="home")
    away = Team(canonical_name="Away", normalized_name="away")
    session.add_all([competition, home, away])
    session.flush()
    match = Match(competition_id=competition.id, home_team_id=home.id, away_team_id=away.id)
    session.add(match)
    session.commit()

    output = PoissonModel().predict(FeatureBuilder(session).build(match.id))

    assert output.model_status == "not_available"
    assert output.reason is not None
