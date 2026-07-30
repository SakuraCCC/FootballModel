from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Competition, DataSource, Match, RawDataSnapshot, Season, Team
from app.services.ingestion.base import BaseProvider, ProviderResponse
from app.services.normalization import normalize_competition, normalize_match
from app.services.normalization.match import NormalizedMatch
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
        return snapshot

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
