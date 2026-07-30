from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ActualResult, Match, MatchStatistic, RawDataSnapshot
from app.services.prediction.features.match_features import HistoricalResult, MatchFeatures
from app.services.prediction.features.team_features import TeamFeatures


class FeatureBuilder:
    """Builds model inputs solely from normalized, persisted system data."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def build(self, match_id: str) -> MatchFeatures:
        match = self._session.get(Match, match_id)
        if match is None:
            raise ValueError("Match was not found")
        history = self._historical_results(match)
        home_team = self._team_features(match.home_team_id, match.kickoff_at, history, is_home=True)
        away_team = self._team_features(
            match.away_team_id, match.kickoff_at, history, is_home=False
        )
        league_average = self._league_average_goals(history)
        snapshot_id = self._latest_snapshot_id(match.source_id, match.kickoff_at)
        missing_fields = self._missing_fields(
            match, home_team, away_team, league_average, snapshot_id
        )
        return MatchFeatures(
            match_id=match.id,
            competition_id=match.competition_id,
            home_team=home_team,
            away_team=away_team,
            league_average_goals=league_average,
            data_completeness=self._completeness(missing_fields),
            missing_fields=missing_fields,
            input_snapshot_id=snapshot_id,
            historical_results=history,
        )

    def _historical_results(self, match: Match) -> list[HistoricalResult]:
        if match.kickoff_at is None:
            return []
        statement = (
            select(Match, ActualResult)
            .join(ActualResult, ActualResult.match_id == Match.id)
            .where(
                Match.competition_id == match.competition_id,
                Match.kickoff_at < match.kickoff_at,
                ActualResult.completed_at.is_not(None),
                ActualResult.completed_at <= match.kickoff_at,
            )
            .order_by(Match.kickoff_at.asc())
        )
        return [
            HistoricalResult(
                match_id=historic_match.id,
                kickoff_at=historic_match.kickoff_at,
                home_team_id=historic_match.home_team_id,
                away_team_id=historic_match.away_team_id,
                home_score=result.home_score,
                away_score=result.away_score,
            )
            for historic_match, result in self._session.execute(statement)
            if historic_match.kickoff_at is not None
        ]

    def _team_features(
        self,
        team_id: str | None,
        kickoff_at: datetime | None,
        history: list[HistoricalResult],
        *,
        is_home: bool,
    ) -> TeamFeatures:
        if team_id is None:
            return TeamFeatures(None, None, None, None, None, None, None, None, None, None, 0)
        team_history = [
            item for item in history if item.home_team_id == team_id or item.away_team_id == team_id
        ][-5:]
        if not team_history:
            return TeamFeatures(team_id, None, None, None, None, None, None, None, None, None, 0)
        form = [self._result_for_team(item, team_id) for item in team_history]
        goals_for = [self._goals_for(item, team_id) for item in team_history]
        goals_against = [self._goals_against(item, team_id) for item in team_history]
        statistics = self._statistics_for(team_id, [item.match_id for item in team_history])
        shots = [
            statistics[item.match_id].shots
            for item in team_history
            if statistics.get(item.match_id) and statistics[item.match_id].shots is not None
        ]
        xg = [
            statistics[item.match_id].xg
            for item in team_history
            if statistics.get(item.match_id) and statistics[item.match_id].xg is not None
        ]
        home_form = [
            self._result_for_team(item, team_id)
            for item in team_history
            if item.home_team_id == team_id
        ]
        away_form = [
            self._result_for_team(item, team_id)
            for item in team_history
            if item.away_team_id == team_id
        ]
        latest = team_history[-1].kickoff_at
        rest_days = (kickoff_at.date() - latest.date()).days if kickoff_at else None
        return TeamFeatures(
            team_id=team_id,
            recent_form=form,
            recent_goals_for=sum(goals_for) / len(goals_for),
            recent_goals_against=sum(goals_against) / len(goals_against),
            home_form=home_form or None,
            away_form=away_form or None,
            league_rank=None,
            points=None,
            goal_difference=None,
            rest_days=rest_days,
            historical_match_count=len(team_history),
            recent_goals_trend=self._trend(goals_for),
            recent_conceded_trend=self._trend(goals_against),
            recent_shots_trend=self._trend(shots),
            recent_xg_trend=self._trend(xg),
        )

    def _statistics_for(self, team_id: str, match_ids: list[str]) -> dict[str, MatchStatistic]:
        if not match_ids:
            return {}
        rows = self._session.scalars(
            select(MatchStatistic).where(
                MatchStatistic.team_id == team_id, MatchStatistic.match_id.in_(match_ids)
            )
        )
        return {item.match_id: item for item in rows}

    @staticmethod
    def _trend(values: list[float | int]) -> float | None:
        if len(values) < 2:
            return None
        return round((float(values[-1]) - float(values[0])) / (len(values) - 1), 4)

    @staticmethod
    def _result_for_team(item: HistoricalResult, team_id: str) -> str:
        goals_for = FeatureBuilder._goals_for(item, team_id)
        goals_against = FeatureBuilder._goals_against(item, team_id)
        return "W" if goals_for > goals_against else "D" if goals_for == goals_against else "L"

    @staticmethod
    def _goals_for(item: HistoricalResult, team_id: str) -> int:
        return item.home_score if item.home_team_id == team_id else item.away_score

    @staticmethod
    def _goals_against(item: HistoricalResult, team_id: str) -> int:
        return item.away_score if item.home_team_id == team_id else item.home_score

    @staticmethod
    def _league_average_goals(history: list[HistoricalResult]) -> float | None:
        if not history:
            return None
        return sum(item.home_score + item.away_score for item in history) / len(history)

    def _latest_snapshot_id(self, source_id: str | None, kickoff_at: datetime | None) -> str | None:
        if source_id is None or kickoff_at is None:
            return None
        snapshot = self._session.scalar(
            select(RawDataSnapshot)
            .where(
                RawDataSnapshot.data_source_id == source_id,
                RawDataSnapshot.retrieved_at <= kickoff_at,
            )
            .order_by(RawDataSnapshot.retrieved_at.desc())
        )
        return snapshot.id if snapshot else None

    @staticmethod
    def _missing_fields(
        match: Match,
        home_team: TeamFeatures,
        away_team: TeamFeatures,
        league_average: float | None,
        snapshot_id: str | None,
    ) -> list[str]:
        fields = []
        if match.kickoff_at is None:
            fields.append("match.kickoff_at")
        if match.home_team_id is None or match.away_team_id is None:
            fields.append("match.teams")
        if home_team.historical_match_count < 3:
            fields.append("home_team.historical_results")
        if away_team.historical_match_count < 3:
            fields.append("away_team.historical_results")
        if league_average is None:
            fields.append("league_average_goals")
        if snapshot_id is None:
            fields.append("input_snapshot")
        fields.extend(["league_rank", "points", "goal_difference", "injuries"])
        if home_team.recent_shots_trend is None:
            fields.append("home_team.shots")
        if away_team.recent_shots_trend is None:
            fields.append("away_team.shots")
        if home_team.recent_xg_trend is None:
            fields.append("home_team.xg")
        if away_team.recent_xg_trend is None:
            fields.append("away_team.xg")
        return fields

    @staticmethod
    def _completeness(missing_fields: list[str]) -> str:
        core_missing = {
            "match.kickoff_at",
            "match.teams",
            "home_team.historical_results",
            "away_team.historical_results",
            "league_average_goals",
        }
        if any(field in core_missing for field in missing_fields):
            return "low"
        if missing_fields:
            return "medium"
        return "high"
