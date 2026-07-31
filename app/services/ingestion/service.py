"""Provider response persistence and normalization."""
# The ingestion mappings intentionally keep provider fields adjacent to their persistence updates.
# ruff: noqa: E702

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models import (
    ActualResult,
    Competition,
    CompetitionCoverage,
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


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestionSummary:
    source_name: str
    snapshot_id: str
    processed: int
    saved: int
    skipped: int
    quality_levels: dict[str, int]


class IngestionService:
    def __init__(self, session: Session, provider: BaseProvider, settings: Settings | None = None) -> None:
        self._session = session
        self._provider = provider
        self._settings = settings or get_settings()

    @property
    def data_mode(self) -> str:
        return self._settings.football_data_mode.lower()

    def _ensure_external_allowed(self) -> None:
        if self.data_mode in {"offline", "manual"}:
            raise IngestionError(f"external_provider_disabled:data_mode={self.data_mode}")

    @staticmethod
    def _request_hash(endpoint: str, params: dict[str, object]) -> str:
        normalized = {key: params[key] for key in sorted(params) if params[key] is not None}
        return hashlib.sha256(f"{endpoint}:{json.dumps(normalized, sort_keys=True, default=str)}".encode()).hexdigest()

    def _quota_remaining(self) -> int | None:
        usage = self._session.scalar(
            select(ProviderQuotaUsage).order_by(ProviderQuotaUsage.last_retrieved_at.desc())
        )
        if usage is None:
            return None
        if self._settings.api_football_plan_mode in {"auto", "free"} and usage.request_count >= self._settings.api_football_daily_soft_limit:
            return 0
        return usage.daily_remaining

    def _assert_budget(self, kind: str) -> None:
        usage = self._session.scalar(
            select(ProviderQuotaUsage).order_by(ProviderQuotaUsage.last_retrieved_at.desc())
        )
        remaining = usage.daily_remaining if usage else None
        if usage and kind != "status" and self._settings.api_football_plan_mode in {"auto", "free"} and usage.request_count >= self._settings.api_football_daily_soft_limit:
            remaining = 0
        if remaining is None:
            return
        if remaining <= 0:
            raise IngestionError("quota_exhausted")
        optional = kind in {"players", "injuries", "statistics", "standings", "coverage"}
        if optional and remaining <= self._settings.api_football_daily_reserve:
            raise IngestionError(f"quota_critical:reserved:{kind}:remaining={remaining}")
        if optional and remaining < self._settings.api_football_min_remaining_for_optional:
            if kind == "lineups" and remaining >= self._settings.api_football_min_remaining_for_lineup:
                return
            raise IngestionError(f"quota_low:deferred_{kind}:remaining={remaining}")
        if kind == "lineups" and remaining < self._settings.api_football_min_remaining_for_lineup:
            raise IngestionError(f"quota_critical:deferred_lineups:remaining={remaining}")

    def _provider_call(
        self,
        endpoint: str,
        params: dict[str, object],
        callback,
        *,
        cache_window: timedelta,
        kind: str = "core",
    ) -> ProviderResponse:
        request_hash = self._request_hash(endpoint, params)
        now = datetime.now(UTC)
        cached = self._session.scalar(
            select(RawDataSnapshot).where(
                RawDataSnapshot.provider == self._provider.provider_name,
                RawDataSnapshot.endpoint == endpoint,
                RawDataSnapshot.request_hash == request_hash,
                RawDataSnapshot.cache_expires_at > now,
            ).order_by(RawDataSnapshot.retrieved_at.desc())
        )
        if cached is not None:
            logger.info("provider_cache_hit provider=%s endpoint=%s", self._provider.provider_name, endpoint)
            payload = cached.response_json
            data = payload.get("response") if isinstance(payload, dict) else []
            if isinstance(data, dict):
                data = [data]
            if not isinstance(data, list):
                data = []
            return ProviderResponse(
                provider=cached.provider,
                endpoint=cached.endpoint,
                request_time=cached.request_time,
                retrieved_at=cached.retrieved_at,
                response_json=payload,
                data=data,
                snapshot_id=cached.id,
                cached=True,
            )
        self._ensure_external_allowed()
        self._assert_budget(kind)
        response = callback()
        object.__setattr__(response, "snapshot_id", request_hash)
        logger.info("provider_request provider=%s endpoint=%s", self._provider.provider_name, endpoint)
        return response

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
        if response.cached and response.snapshot_id:
            snapshot = self._session.get(RawDataSnapshot, response.snapshot_id)
            if snapshot is not None:
                return snapshot
        request_hash = response.snapshot_id if response.snapshot_id and len(response.snapshot_id) == 64 else None
        snapshot = RawDataSnapshot(
            data_source_id=source.id,
            provider=response.provider,
            endpoint=response.endpoint,
            request_time=response.request_time,
            response_json=response.response_json,
            retrieved_at=response.retrieved_at,
            request_hash=request_hash,
            cached=False,
            cache_expires_at=response.retrieved_at + self._cache_window(response.endpoint),
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
        usage.request_count = (usage.request_count or 0) + max(response.request_attempts, 1)
        usage.quota_limit = self._to_int(quota.get("daily_limit") or quota.get("x-ratelimit-requests-limit"))
        usage.remaining = self._to_int(quota.get("daily_remaining") or quota.get("x-ratelimit-requests-remaining"))
        parsed_daily_limit = self._to_int(quota.get("daily_limit"))
        parsed_daily_remaining = self._to_int(quota.get("daily_remaining"))
        usage.daily_limit = parsed_daily_limit if parsed_daily_limit is not None else usage.quota_limit
        usage.daily_remaining = parsed_daily_remaining if parsed_daily_remaining is not None else usage.remaining
        usage.minute_limit = self._to_int(quota.get("minute_limit") or quota.get("x-ratelimit-requests-limit-minute"))
        usage.minute_remaining = self._to_int(quota.get("minute_remaining") or quota.get("x-ratelimit-requests-remaining-minute"))
        usage.last_checked_at = response.retrieved_at
        usage.quota_state = self._quota_state(usage.daily_remaining)
        usage.last_status = response.status_code
        usage.last_retrieved_at = response.retrieved_at
        return snapshot

    def _cache_window(self, endpoint: str) -> timedelta:
        days = self._settings.provider_coverage_cache_days if endpoint == "leagues" else 1
        if endpoint == "status":
            return timedelta(hours=self._settings.provider_status_cache_hours)
        if endpoint in {"teams"}:
            return timedelta(days=30)
        if endpoint in {"players", "standings"}:
            return timedelta(days=7 if endpoint == "players" else 1)
        if endpoint in {"fixtures"}:
            return timedelta(hours=12)
        if endpoint in {"fixtures/lineups", "injuries"}:
            return timedelta(hours=3)
        if endpoint in {"fixtures/statistics"}:
            return timedelta(days=3650)
        return timedelta(days=days)

    @staticmethod
    def _quota_state(remaining: int | None) -> str:
        if remaining is None:
            return "unknown"
        if remaining <= 0:
            return "quota_exhausted"
        if remaining <= 20:
            return "quota_critical"
        if remaining <= 40:
            return "quota_low"
        return "normal"

    @staticmethod
    def _to_int(value: object) -> int | None:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def sync_competitions(self, *, season: int | None = None) -> IngestionSummary:
        response = self._provider_call(
            "leagues", {"season": season}, lambda: self._provider.get_competitions(season=season),
            cache_window=timedelta(days=self._settings.provider_coverage_cache_days), kind="coverage",
        )
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
        match_date_value = match_date.isoformat() if match_date else None
        response = self._provider_call(
            "fixtures", {"league": competition.api_football_league_id, "season": season, "date": match_date_value},
            lambda: self._provider.get_matches(league_id=competition.api_football_league_id, season=season, match_date=match_date_value),
            cache_window=timedelta(hours=12), kind="core",
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
        self._ensure_coverage(competition, season, "standings")
        if competition.api_football_league_id is None:
            raise IngestionError(f"API-Football league mapping is unavailable for {competition_code}")
        response = self._provider_call(
            "standings", {"league": competition.api_football_league_id, "season": season},
            lambda: self._provider.get_standings(league_id=competition.api_football_league_id, season=season),
            cache_window=timedelta(hours=12), kind="standings",
        )
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
        self._ensure_coverage(self._competition(competition_code), season or self._settings.target_season, "players")
        response = self._provider_call(
            "players", {"team": team_id, "season": season},
            lambda: self._provider.get_players(team_id=team_id, season=season),
            cache_window=timedelta(days=7), kind="players",
        )
        source = self._source(); snapshot = self._snapshot(source, response)
        competition = self._competition(competition_code)
        season_record = self._get_or_create_season(competition, season or self._settings.target_season, source)
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
        self._ensure_coverage(competition, season, "injuries")
        if competition.api_football_league_id is None:
            raise IngestionError(f"API-Football league mapping is unavailable for {competition_code}")
        response = self._provider_call(
            "injuries", {"league": competition.api_football_league_id, "season": season, "fixture": fixture_id},
            lambda: self._provider.get_injuries(league_id=competition.api_football_league_id, season=season, fixture_id=fixture_id),
            cache_window=timedelta(hours=3), kind="injuries",
        )
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
        competition = self._session.get(Competition, match.competition_id)
        season = self._session.get(Season, match.season_id) if match.season_id else None
        if competition is not None and season is not None:
            self._ensure_coverage(competition, int(season.code), "lineups")
        response = self._provider_call(
            "fixtures/lineups", {"fixture": fixture_id}, lambda: self._provider.get_lineups(fixture_id=fixture_id),
            cache_window=timedelta(hours=3), kind="lineups",
        ); source = self._source(); snapshot = self._snapshot(source, response); saved = 0
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
        competition = self._session.get(Competition, match.competition_id)
        season = self._session.get(Season, match.season_id) if match.season_id else None
        if competition is not None and season is not None:
            self._ensure_coverage(competition, int(season.code), "statistics")
        if (match.status or "").casefold() not in {"finished", "completed", "ft", "aet", "pen"}:
            raise IngestionError("statistics_only_allowed_for_completed_match")
        response = self._provider_call(
            "fixtures/statistics", {"fixture": fixture_id}, lambda: self._provider.get_statistics(fixture_id=fixture_id),
            cache_window=timedelta(days=3650), kind="statistics",
        ); source = self._source(); snapshot = self._snapshot(source, response); saved = 0
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
        match_date_value = match_date.isoformat() if match_date else None
        response = self._provider_call(
            "fixtures", {"league": competition.api_football_league_id, "season": season, "date": match_date_value},
            lambda: self._provider.get_matches(league_id=competition.api_football_league_id, season=season, match_date=match_date_value),
            cache_window=timedelta(hours=12), kind="core",
        )
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

    def _ensure_coverage(self, competition: Competition, season: int, field: str | None) -> None:
        season_record = self._session.scalar(
            select(Season).where(Season.competition_id == competition.id, Season.code == str(season))
        )
        now = datetime.now(UTC)
        coverage = self._session.scalar(
            select(CompetitionCoverage).where(
                CompetitionCoverage.competition_id == competition.id,
                CompetitionCoverage.season_id == (season_record.id if season_record else ""),
                CompetitionCoverage.expires_at > now,
            )
        ) if season_record else None
        if coverage is None:
            summary = self.sync_competitions(season=season)
            snapshot = self._session.get(RawDataSnapshot, summary.snapshot_id)
            season_record = self._get_or_create_season(competition, season, self._source())
            payload = {}
            if snapshot and isinstance(snapshot.response_json, dict):
                for item in snapshot.response_json.get("response", []):
                    league = item.get("league", {}) if isinstance(item, dict) else {}
                    if str(league.get("id")) == str(competition.api_football_league_id):
                        payload = item.get("coverage") or {}
                        break
            coverage = CompetitionCoverage(
                competition_id=competition.id,
                season_id=season_record.id,
                coverage=payload,
                source_snapshot_id=snapshot.id if snapshot else None,
                retrieved_at=snapshot.retrieved_at if snapshot else now,
                expires_at=(snapshot.retrieved_at if snapshot else now) + timedelta(days=self._settings.provider_coverage_cache_days),
                certainty="reported",
            )
            self._session.add(coverage)
            self._session.commit()
        if field is None:
            return
        value = self._coverage_value(coverage.coverage, field)
        if value is not True:
            # Older in-process adapters do not expose a coverage endpoint. Keep their
            # backwards-compatible behavior while the real ApiFootballProvider is strict.
            if type(self._provider).get_status is BaseProvider.get_status:
                return
            raise IngestionError(f"coverage_unavailable:{field}")

    @staticmethod
    def _coverage_value(payload: dict, field: str) -> object:
        if not isinstance(payload, dict):
            return None
        if field in payload:
            return payload[field]
        fixtures = payload.get("fixtures")
        if isinstance(fixtures, dict):
            aliases = {
                "lineups": "lineups",
                "statistics": "statistics_fixtures",
                "injuries": "events",
            }
            return fixtures.get(aliases.get(field, field))
        return None

    def provider_status(self) -> dict:
        response = self._provider_call(
            "status", {}, lambda: self._provider.get_status(),
            cache_window=timedelta(hours=self._settings.provider_status_cache_hours), kind="status",
        )
        source = self._source()
        snapshot = self._snapshot(source, response)
        item = response.data[0] if response.data and isinstance(response.data[0], dict) else {}
        account = item.get("account", {}) if isinstance(item.get("account"), dict) else {}
        plan = account.get("plan", {}) if isinstance(account.get("plan"), dict) else {}
        requests = item.get("requests", {}) if isinstance(item.get("requests"), dict) else {}
        quota = response.quota or {}
        daily_limit = self._to_int(requests.get("limit_day") or plan.get("quota_per_day") or quota.get("daily_limit") or quota.get("x-ratelimit-requests-limit"))
        daily_used = self._to_int(requests.get("current"))
        daily_remaining = (daily_limit - daily_used) if daily_limit is not None and daily_used is not None else self._to_int(quota.get("daily_remaining") or quota.get("x-ratelimit-requests-remaining"))
        usage = self._session.scalar(select(ProviderQuotaUsage).where(ProviderQuotaUsage.source_id == source.id, ProviderQuotaUsage.usage_date == snapshot.retrieved_at.date()))
        if usage is None:
            usage = next(
                (item for item in self._session.new if isinstance(item, ProviderQuotaUsage) and item.source_id == source.id and item.usage_date == snapshot.retrieved_at.date()),
                None,
            )
        if usage is None:
            usage = ProviderQuotaUsage(source_id=source.id, usage_date=snapshot.retrieved_at.date())
            self._session.add(usage)
        usage.plan_name = plan.get("name") if isinstance(plan.get("name"), str) else None
        usage.daily_limit = daily_limit
        usage.daily_remaining = daily_remaining
        usage.remaining = daily_remaining
        usage.quota_limit = daily_limit
        usage.minute_limit = self._to_int(
            requests.get("limit_minute")
            or quota.get("minute_limit")
            or quota.get("x-ratelimit-requests-limit-minute")
        )
        usage.minute_remaining = self._to_int(
            quota.get("minute_remaining")
            or quota.get("x-ratelimit-requests-remaining-minute")
        )
        usage.last_checked_at = snapshot.retrieved_at
        usage.quota_state = self._quota_state(daily_remaining)
        self._session.commit()
        return {
            "plan_name": usage.plan_name,
            "daily_limit": usage.daily_limit,
            "daily_remaining": usage.daily_remaining,
            "minute_limit": usage.minute_limit,
            "minute_remaining": usage.minute_remaining,
            "quota_state": usage.quota_state,
            "snapshot_id": snapshot.id,
            "cached": response.cached,
        }

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
