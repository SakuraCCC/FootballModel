"""Provider response persistence and normalization."""
# The ingestion mappings intentionally keep provider fields adjacent to their persistence updates.
# ruff: noqa: E702

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ActualResult,
    Competition,
    CompetitionStanding,
    DataSource,
    Injury,
    Match,
    MatchLineup,
    MatchStatistic,
    Player,
    PlayerSeasonStat,
    ProviderQuotaUsage,
    RawDataSnapshot,
    Season,
    Team,
)
from app.services.ingestion.base import BaseProvider, ProviderResponse
from app.services.normalization import normalize_competition, normalize_match
from app.services.normalization.match import NormalizedMatch
from app.services.normalization.player import normalize_player
from app.services.normalization.team import NormalizedTeam
from app.services.quality import assess_match_completeness


class IngestionError(RuntimeError):
    pass


@dataclass(frozen=True)
class IngestionSummary:
    source_name: str
    snapshot_id: str
    processed: int
    saved: int
    skipped: int
    quality_levels: dict[str, int]


class IngestionService:
    def __init__(self, session: Session, provider: BaseProvider) -> None:
        self._session = session
        self._provider = provider

    def _source(self) -> DataSource:
        source = self._session.scalar(
            select(DataSource).where(
                DataSource.source_name == self._provider.provider_name,
                DataSource.api_version == self._provider.api_version,
            )
        )
        if source is None:
            source = DataSource(
                name=f"{self._provider.provider_name}-{self._provider.api_version}",
                source_name=self._provider.provider_name,
                source_type="football_data_api",
                source_tier=self._provider.source_tier,
                api_version=self._provider.api_version,
                reliability_level="reported",
                metadata_={},
            )
            self._session.add(source)
            self._session.flush()
        return source

    def _snapshot(self, source: DataSource, response: ProviderResponse) -> RawDataSnapshot:
        snapshot = RawDataSnapshot(
            data_source_id=source.id,
            provider=response.provider,
            endpoint=response.endpoint,
            request_time=response.request_time,
            response_json=response.response_json,
            retrieved_at=response.retrieved_at,
        )
        self._session.add(snapshot)
        self._session.flush()
        quota = response.quota or {}
        usage = self._session.scalar(
            select(ProviderQuotaUsage).where(
                ProviderQuotaUsage.source_id == source.id,
                ProviderQuotaUsage.usage_date == response.retrieved_at.date(),
            )
        )
        if usage is None:
            usage = ProviderQuotaUsage(source_id=source.id, usage_date=response.retrieved_at.date())
            self._session.add(usage)
        usage.request_count = (usage.request_count or 0) + 1
        usage.quota_limit = self._to_int(quota.get("x-ratelimit-requests-limit"))
        usage.remaining = self._to_int(quota.get("x-ratelimit-requests-remaining"))
        usage.last_status = response.status_code
        usage.last_retrieved_at = response.retrieved_at
        return snapshot

    @staticmethod
    def _to_int(value: object) -> int | None:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def sync_competitions(self, *, season: int | None = None) -> IngestionSummary:
        response = self._provider.get_competitions(season=season)
        source = self._source()
        snapshot = self._snapshot(source, response)
        saved = 0
        skipped = 0
        for payload in response.data:
            normalized = normalize_competition(payload)
            if normalized.code is None or normalized.external_id is None:
                skipped += 1
                continue
            competition = self._session.scalar(
                select(Competition).where(Competition.code == normalized.code)
            )
            if competition is None:
                skipped += 1
                continue
            competition.api_football_league_id = normalized.external_id
            competition.provider_name = normalized.provider_name
            competition.certainty = normalized.certainty
            saved += 1
        self._session.commit()
        return IngestionSummary(
            source_name=source.source_name,
            snapshot_id=snapshot.id,
            processed=len(response.data),
            saved=saved,
            skipped=skipped,
            quality_levels={},
        )

    def sync_matches(
        self, *, competition_code: str, season: int, match_date: date | None = None
    ) -> IngestionSummary:
        competition = self._session.scalar(
            select(Competition).where(Competition.code == competition_code.upper())
        )
        if competition is None:
            raise IngestionError(f"Unsupported competition code: {competition_code}")
        if competition.api_football_league_id is None:
            self.sync_competitions(season=season)
            competition = self._session.scalar(
                select(Competition).where(Competition.code == competition_code.upper())
            )
        if competition is None or competition.api_football_league_id is None:
            raise IngestionError(
                f"API-Football league mapping is unavailable for {competition_code}; "
                "synchronize competitions first."
            )
        response = self._provider.get_matches(
            league_id=competition.api_football_league_id,
            season=season,
            match_date=match_date.isoformat() if match_date else None,
        )
        source = self._source()
        snapshot = self._snapshot(source, response)
        season_record = self._get_or_create_season(competition, season, source)
        saved = 0
        skipped = 0
        quality_levels: dict[str, int] = {"high": 0, "medium": 0, "low": 0}
        for payload in response.data:
            normalized = normalize_match(payload)
            if competition.code == "UCL_QUALIFIER" and not self._is_ucl_qualifier(normalized):
                skipped += 1
                continue
            self._upsert_match(competition, season_record, source, normalized)
            quality = assess_match_completeness(normalized)
            quality_levels[quality.level] += 1
            saved += 1
        self._session.commit()
        return IngestionSummary(
            source_name=source.source_name,
            snapshot_id=snapshot.id,
            processed=len(response.data),
            saved=saved,
            skipped=skipped,
            quality_levels={level: count for level, count in quality_levels.items() if count},
        )

    def sync_standings(self, *, competition_code: str, season: int) -> IngestionSummary:
        competition = self._competition(competition_code)
        if competition.api_football_league_id is None:
            raise IngestionError(f"API-Football league mapping is unavailable for {competition_code}")
        response = self._provider.get_standings(league_id=competition.api_football_league_id, season=season)
        source = self._source()
        snapshot = self._snapshot(source, response)
        season_record = self._get_or_create_season(competition, season, source)
        rows = response.data[0].get("league", {}).get("standings", []) if response.data else []
        entries = [row for group in rows if isinstance(group, list) for row in group if isinstance(row, dict)]
        saved = 0
        for row in entries:
            team_payload = row.get("team") if isinstance(row.get("team"), dict) else {}
            team = self._upsert_team_from_payload(team_payload, source)
            if team is None:
                continue
            goals = row.get("all", {}).get("goals", {}) if isinstance(row.get("all"), dict) else {}
            standing = self._session.scalar(select(CompetitionStanding).where(
                CompetitionStanding.competition_id == competition.id,
                CompetitionStanding.season_id == season_record.id,
                CompetitionStanding.team_id == team.id,
            ))
            if standing is None:
                standing = CompetitionStanding(competition_id=competition.id, season_id=season_record.id, team_id=team.id)
                self._session.add(standing)
            standing.rank = self._to_int(row.get("rank")); standing.points = self._to_int(row.get("points"))
            standing.goals_for = self._to_int(goals.get("for")); standing.goals_against = self._to_int(goals.get("against"))
            standing.goal_difference = self._to_int(row.get("goalsDiff")); standing.form = row.get("form") if isinstance(row.get("form"), str) else None
            standing.source_snapshot_id = snapshot.id; standing.certainty = "reported"
            saved += 1
        self._session.commit()
        return self._summary(source, snapshot, len(response.data), saved)

    def sync_players(self, *, team_id: int, season: int | None = None, competition_code: str = "CSL") -> IngestionSummary:
        response = self._provider.get_players(team_id=team_id, season=season)
        source = self._source(); snapshot = self._snapshot(source, response)
        competition = self._competition(competition_code)
        season_record = self._get_or_create_season(competition, season or 0, source)
        saved = 0
        for payload in response.data:
            normalized = normalize_player(payload)
            if not normalized.external_id or not normalized.canonical_name:
                continue
            player = self._session.scalar(select(Player).where(Player.source_id == source.id, Player.external_id == normalized.external_id))
            if player is None:
                player = Player(canonical_name=normalized.canonical_name, normalized_name=normalized.normalized_name or normalized.canonical_name.casefold(), external_id=normalized.external_id, source_id=source.id, certainty="reported")
                self._session.add(player); self._session.flush()
            player.canonical_name = normalized.canonical_name; player.normalized_name = normalized.normalized_name or normalized.canonical_name.casefold(); player.certainty = "reported"
            statistics = payload.get("statistics") if isinstance(payload.get("statistics"), list) else []
            stat_payload = statistics[0] if statistics and isinstance(statistics[0], dict) else {}
            games = stat_payload.get("games") if isinstance(stat_payload.get("games"), dict) else {}
            goals = stat_payload.get("goals") if isinstance(stat_payload.get("goals"), dict) else {}
            stat = self._session.scalar(select(PlayerSeasonStat).where(PlayerSeasonStat.player_id == player.id, PlayerSeasonStat.season_id == season_record.id))
            if stat is None:
                stat = PlayerSeasonStat(player_id=player.id, season_id=season_record.id); self._session.add(stat)
            stat.team_id = self._team_by_external(source.id, str(team_id)).id if self._team_by_external(source.id, str(team_id)) else None
            stat.position = games.get("position") if isinstance(games.get("position"), str) else None
            stat.minutes_played = self._to_int(games.get("minutes")); stat.appearances = self._to_int(games.get("appearences")); stat.goals = self._to_int(goals.get("total")); stat.assists = self._to_int(goals.get("assists")); stat.source_snapshot_id = snapshot.id; stat.certainty = "reported"
            saved += 1
        self._session.commit(); return self._summary(source, snapshot, len(response.data), saved)

    def sync_injuries(self, *, competition_code: str, season: int, fixture_id: int | None = None) -> IngestionSummary:
        competition = self._competition(competition_code)
        if competition.api_football_league_id is None:
            raise IngestionError(f"API-Football league mapping is unavailable for {competition_code}")
        response = self._provider.get_injuries(league_id=competition.api_football_league_id, season=season, fixture_id=fixture_id)
        source = self._source(); snapshot = self._snapshot(source, response); saved = 0
        match = self._session.scalar(select(Match).where(Match.source_id == source.id, Match.external_id == str(fixture_id))) if fixture_id else None
        for payload in response.data:
            player_payload = payload.get("player") if isinstance(payload.get("player"), dict) else {}
            team_payload = payload.get("team") if isinstance(payload.get("team"), dict) else {}
            team = self._upsert_team_from_payload(team_payload, source)
            player = self._upsert_player_from_payload(player_payload, team, source)
            external_id = str(player_payload.get("id")) if player_payload.get("id") is not None else None
            record = self._session.scalar(select(Injury).where(Injury.external_id == external_id, Injury.match_id == (match.id if match else None), Injury.player_id == (player.id if player else None))) if external_id else None
            if record is None:
                record = Injury(external_id=external_id, match_id=match.id if match else None, player_id=player.id if player else None)
                self._session.add(record)
            record.team_id = team.id if team else None
            record.status = player_payload.get("reason") if isinstance(player_payload.get("reason"), str) else None
            record.reason = player_payload.get("reason") if isinstance(player_payload.get("reason"), str) else None
            record.injury_type = player_payload.get("type") if isinstance(player_payload.get("type"), str) else None
            record.source_snapshot_id = snapshot.id; record.certainty = "reported"; saved += 1
        self._session.commit(); return self._summary(source, snapshot, len(response.data), saved)

    def sync_lineups(self, *, match_id: str, fixture_id: int) -> IngestionSummary:
        match = self._session.get(Match, match_id)
        if match is None:
            raise IngestionError("Match was not found")
        response = self._provider.get_lineups(fixture_id=fixture_id); source = self._source(); snapshot = self._snapshot(source, response); saved = 0
        match.lineup_status = "reported" if response.data else "unavailable"
        for team_payload in response.data:
            team_info = team_payload.get("team") if isinstance(team_payload.get("team"), dict) else {}
            team = self._upsert_team_from_payload(team_info, source)
            if team is None:
                continue
            for entry in team_payload.get("startXI", []) + team_payload.get("substitutes", []):
                player_payload = entry.get("player") if isinstance(entry, dict) and isinstance(entry.get("player"), dict) else {}
                player = self._upsert_player_from_payload(player_payload, team, source)
                external_player_id = str(player_payload.get("id")) if player_payload.get("id") is not None else None
                lineup = self._session.scalar(select(MatchLineup).where(MatchLineup.match_id == match.id, MatchLineup.team_id == team.id, MatchLineup.external_player_id == external_player_id)) if external_player_id else None
                if lineup is None:
                    lineup = MatchLineup(match_id=match.id, team_id=team.id, external_player_id=external_player_id)
                    self._session.add(lineup)
                lineup.player_id = player.id if player else None; lineup.player_name = player_payload.get("name") if isinstance(player_payload.get("name"), str) else None; lineup.starter = entry in team_payload.get("startXI", []); lineup.position = player_payload.get("pos") if isinstance(player_payload.get("pos"), str) else None; lineup.jersey = self._to_int(player_payload.get("number")); lineup.source_snapshot_id = snapshot.id; lineup.certainty = "reported"; saved += 1
        self._session.commit(); return self._summary(source, snapshot, len(response.data), saved)

    def sync_statistics(self, *, match_id: str, fixture_id: int) -> IngestionSummary:
        match = self._session.get(Match, match_id)
        if match is None:
            raise IngestionError("Match was not found")
        response = self._provider.get_statistics(fixture_id=fixture_id); source = self._source(); snapshot = self._snapshot(source, response); saved = 0
        for payload in response.data:
            team_payload = payload.get("team") if isinstance(payload.get("team"), dict) else {}
            team = self._upsert_team_from_payload(team_payload, source)
            if team is None:
                continue
            values = {str(item.get("type", "")).casefold(): item.get("value") for item in payload.get("statistics", []) if isinstance(item, dict)}
            stat = self._session.scalar(select(MatchStatistic).where(MatchStatistic.match_id == match.id, MatchStatistic.team_id == team.id))
            if stat is None:
                stat = MatchStatistic(match_id=match.id, team_id=team.id); self._session.add(stat)
            stat.shots = self._to_int(values.get("total shots")); stat.shots_on_target = self._to_int(values.get("shots on goal")); stat.possession = self._percent(values.get("ball possession")); stat.corners = self._to_int(values.get("corner kicks")); stat.xg = self._to_float(values.get("expected goals")); stat.xga = self._to_float(values.get("expected goals against")); stat.certainty = "reported"; stat.source_snapshot_id = snapshot.id; saved += 1
        self._session.commit(); return self._summary(source, snapshot, len(response.data), saved)

    def sync_results(self, *, competition_code: str, season: int, match_date: date | None = None) -> IngestionSummary:
        competition = self._competition(competition_code)
        if competition.api_football_league_id is None:
            raise IngestionError(f"API-Football league mapping is unavailable for {competition_code}")
        response = self._provider.get_matches(league_id=competition.api_football_league_id, season=season, match_date=match_date.isoformat() if match_date else None)
        source = self._source(); snapshot = self._snapshot(source, response); season_record = self._get_or_create_season(competition, season, source); saved = 0
        for payload in response.data:
            normalized = normalize_match(payload)
            self._upsert_match(competition, season_record, source, normalized)
            if normalized.external_id is None or normalized.home_score is None or normalized.away_score is None:
                continue
            match = self._session.scalar(select(Match).where(Match.source_id == source.id, Match.external_id == normalized.external_id))
            if match is None:
                continue
            actual = self._session.scalar(select(ActualResult).where(ActualResult.match_id == match.id))
            if actual is None:
                actual = ActualResult(match_id=match.id); self._session.add(actual)
            actual.home_score = normalized.home_score; actual.away_score = normalized.away_score
            actual.result = "home_win" if normalized.home_score > normalized.away_score else "away_win" if normalized.home_score < normalized.away_score else "draw"
            actual.total_goals = normalized.home_score + normalized.away_score; actual.btts_result = normalized.home_score > 0 and normalized.away_score > 0; actual.completed_at = normalized.kickoff_at; actual.result_source_id = source.id; saved += 1
        self._session.commit()
        return self._summary(source, snapshot, len(response.data), saved)

    def _competition(self, code: str) -> Competition:
        competition = self._session.scalar(select(Competition).where(Competition.code == code.upper()))
        if competition is None:
            raise IngestionError(f"Unsupported competition code: {code}")
        return competition

    def _upsert_team_from_payload(self, payload: dict, source: DataSource) -> Team | None:
        from app.services.normalization.team import normalize_team
        normalized = normalize_team({"team": payload})
        return self._upsert_team(normalized, source)

    def _upsert_player_from_payload(self, payload: dict, team: Team | None, source: DataSource) -> Player | None:
        normalized = normalize_player({"player": payload})
        if not normalized.external_id or not normalized.canonical_name:
            return None
        player = self._session.scalar(select(Player).where(Player.source_id == source.id, Player.external_id == normalized.external_id))
        if player is None:
            player = Player(canonical_name=normalized.canonical_name, normalized_name=normalized.normalized_name or normalized.canonical_name.casefold(), external_id=normalized.external_id, source_id=source.id, team_id=team.id if team else None, certainty="reported"); self._session.add(player); self._session.flush()
        else:
            player.team_id = team.id if team else player.team_id
        return player

    def _team_by_external(self, source_id: str, external_id: str) -> Team | None:
        return self._session.scalar(select(Team).where(Team.source_id == source_id, Team.external_id == external_id))

    @staticmethod
    def _to_float(value: object) -> float | None:
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @classmethod
    def _percent(cls, value: object) -> float | None:
        if isinstance(value, str):
            value = value.rstrip("%")
        return cls._to_float(value)

    @staticmethod
    def _summary(source: DataSource, snapshot: RawDataSnapshot, processed: int, saved: int) -> IngestionSummary:
        return IngestionSummary(source_name=source.source_name, snapshot_id=snapshot.id, processed=processed, saved=saved, skipped=processed - saved, quality_levels={})

    def _get_or_create_season(
        self, competition: Competition, season: int, source: DataSource
    ) -> Season:
        record = self._session.scalar(
            select(Season).where(Season.competition_id == competition.id, Season.code == str(season))
        )
        if record is None:
            record = Season(
                competition_id=competition.id,
                code=str(season),
                source_id=source.id,
                certainty="reported",
            )
            self._session.add(record)
            self._session.flush()
        return record

    def _upsert_team(self, normalized: NormalizedTeam, source: DataSource) -> Team | None:
        if normalized.canonical_name is None or normalized.normalized_name is None:
            return None
        team = None
        if normalized.external_id is not None:
            team = self._session.scalar(
                select(Team).where(
                    Team.source_id == source.id,
                    Team.external_id == normalized.external_id,
                )
            )
        if team is None:
            team = self._session.scalar(
                select(Team).where(Team.normalized_name == normalized.normalized_name)
            )
        if team is None:
            team = Team(
                canonical_name=normalized.canonical_name,
                normalized_name=normalized.normalized_name,
                country_code=normalized.country_code,
                external_id=normalized.external_id,
                source_id=source.id,
                certainty=normalized.certainty,
            )
            self._session.add(team)
            self._session.flush()
        return team

    def _upsert_match(
        self,
        competition: Competition,
        season: Season,
        source: DataSource,
        normalized: NormalizedMatch,
    ) -> None:
        home_team = self._upsert_team(normalized.home_team, source)
        away_team = self._upsert_team(normalized.away_team, source)
        match = None
        if normalized.external_id is not None:
            match = self._session.scalar(
                select(Match).where(
                    Match.source_id == source.id,
                    Match.external_id == normalized.external_id,
                )
            )
        if match is None:
            match = Match(
                competition_id=competition.id,
                season_id=season.id,
                home_team_id=home_team.id if home_team else None,
                away_team_id=away_team.id if away_team else None,
                kickoff_at=normalized.kickoff_at,
                status=normalized.status,
                external_id=normalized.external_id,
                source_id=source.id,
                certainty=normalized.certainty,
            )
            self._session.add(match)
            return
        match.season_id = season.id
        match.home_team_id = home_team.id if home_team else None
        match.away_team_id = away_team.id if away_team else None
        match.kickoff_at = normalized.kickoff_at
        match.status = normalized.status
        match.certainty = normalized.certainty

    @staticmethod
    def _is_ucl_qualifier(match: NormalizedMatch) -> bool:
        round_name = (match.round_name or "").casefold()
        return "qualifying" in round_name or "play-offs" in round_name or "playoffs" in round_name
