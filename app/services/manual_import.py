"""Validated single-user imports for CSV/JSON records.

Imports preserve provenance and never silently overwrite conflicting facts.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ActualResult,
    Competition,
    CompetitionStanding,
    DataSource,
    ImportBatch,
    Injury,
    Match,
    MatchLineup,
    MatchStatistic,
    Player,
    RawDataSnapshot,
    Season,
    Team,
)


class ManualImportError(ValueError):
    pass


def parse_payload(payload: Any, fmt: str = "json") -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        rows = payload.get("records", payload.get("data", payload))
        return parse_payload(rows, fmt)
    if not isinstance(payload, str):
        raise ManualImportError("payload must be a JSON object, list, or CSV/JSON string")
    if fmt.lower() == "csv":
        return list(csv.DictReader(io.StringIO(payload)))
    try:
        return parse_payload(json.loads(payload), "json")
    except json.JSONDecodeError as error:
        raise ManualImportError("payload is not valid JSON or CSV") from error


class ManualImportService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def import_records(self, kind: str, request: dict[str, Any]) -> dict[str, Any]:
        records = parse_payload(request.get("records", request.get("payload", [])), request.get("format", "json"))
        if not records:
            raise ManualImportError("records cannot be empty")
        certainty = str(request.get("certainty", "reported")).lower()
        if certainty == "official" and (not request.get("source_name") or not request.get("source_url")):
            raise ManualImportError("official imports require source_name and source_url")
        if certainty not in {"official", "confirmed", "reported", "predicted", "unavailable"}:
            raise ManualImportError("invalid certainty")
        supplied_time = request.get("retrieved_at")
        if isinstance(supplied_time, str):
            try:
                supplied_time = datetime.fromisoformat(supplied_time.replace("Z", "+00:00"))
            except ValueError as error:
                raise ManualImportError("retrieved_at must be an ISO datetime") from error
        now = supplied_time if isinstance(supplied_time, datetime) else datetime.now(UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        batch_id = str(uuid4())
        source = self.session.scalar(select(DataSource).where(DataSource.source_name == request["source_name"], DataSource.source_type == "manual_import"))
        if source is None:
            source = DataSource(name=f"manual-{request['source_name']}", source_name=request["source_name"], source_type="manual_import", source_tier="primary" if certainty == "official" else "secondary", api_version=None, reliability_level=certainty, source_url=request.get("source_url"), metadata_={})
            self.session.add(source)
            self.session.flush()
        batch = ImportBatch(import_batch_id=batch_id, source_name=request["source_name"], source_url=request.get("source_url"), retrieved_at=now, certainty=certainty, imported_by=request.get("imported_by", "admin"), raw_payload={"kind": kind, "records": records})
        self.session.add(batch)
        self.session.flush()
        snapshot = RawDataSnapshot(data_source_id=source.id, provider="manual", endpoint=f"import/{kind}", request_time=now, response_json={"records": records}, retrieved_at=now)
        self.session.add(snapshot)
        self.session.flush()
        saved = 0
        for row in records:
            try:
                saved += getattr(self, f"_save_{kind}")(row, source, snapshot, certainty)
            except (TypeError, ValueError) as error:
                raise ManualImportError(f"invalid_{kind}_record:{error}") from error
        self.session.commit()
        return {"import_batch_id": batch_id, "kind": kind, "processed": len(records), "saved": saved, "certainty": certainty, "snapshot_id": snapshot.id}

    def _competition(self, code: str) -> Competition:
        competition = self.session.scalar(select(Competition).where(Competition.code == str(code).upper()))
        if competition is None:
            raise ManualImportError(f"competition_not_found:{code}")
        return competition

    def _season(self, competition: Competition, code: Any, source: DataSource) -> Season:
        season_code = str(code)
        season = self.session.scalar(select(Season).where(Season.competition_id == competition.id, Season.code == season_code))
        if season is None:
            season = Season(competition_id=competition.id, code=season_code, source_id=source.id, certainty="reported")
            self.session.add(season)
            self.session.flush()
        return season

    def _team(self, row: dict[str, Any], source: DataSource) -> Team:
        name = row.get("team_name") or row.get("name") or row.get("canonical_name")
        if not name:
            raise ManualImportError("team_name is required")
        external_id = str(row["team_id"]) if row.get("team_id") is not None else None
        team = self.session.scalar(select(Team).where(Team.external_id == external_id, Team.source_id == source.id)) if external_id else None
        if team is None:
            team = self.session.scalar(select(Team).where(Team.normalized_name == str(name).casefold()))
        if team is None:
            team = Team(canonical_name=str(name), normalized_name=str(name).casefold(), external_id=external_id, source_id=source.id, certainty="reported")
            self.session.add(team)
            self.session.flush()
        return team

    def _save_matches(self, row: dict[str, Any], source: DataSource, snapshot: RawDataSnapshot, certainty: str) -> int:
        competition = self._competition(row.get("competition_code"))
        season = self._season(competition, row.get("season"), source)
        home = self._team({"name": row.get("home_team") or row.get("home_team_name"), "team_id": row.get("home_team_id")}, source)
        away = self._team({"name": row.get("away_team") or row.get("away_team_name"), "team_id": row.get("away_team_id")}, source)
        external_id = str(row["match_id"]) if row.get("match_id") is not None else None
        match = self.session.scalar(select(Match).where(Match.external_id == external_id, Match.source_id == source.id)) if external_id else None
        if match is None:
            kickoff = row.get("kickoff_at")
            if isinstance(kickoff, str):
                try:
                    kickoff = datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
                except ValueError as error:
                    raise ManualImportError("kickoff_at must be an ISO datetime") from error
            match = Match(competition_id=competition.id, season_id=season.id, home_team_id=home.id, away_team_id=away.id, kickoff_at=kickoff, status=row.get("status", "scheduled"), external_id=external_id, source_id=source.id, certainty=certainty)
            self.session.add(match)
        elif match.home_team_id != home.id or match.away_team_id != away.id:
            raise ManualImportError("match_conflict:home_or_away_team_changed")
        return 1

    def _match(self, row: dict[str, Any]) -> Match:
        match = self.session.get(Match, str(row.get("match_id")))
        if match is None:
            raise ManualImportError("match_not_found")
        return match

    def _save_results(self, row: dict[str, Any], source: DataSource, snapshot: RawDataSnapshot, certainty: str) -> int:
        match = self._match(row)
        home_score, away_score = int(row["home_score"]), int(row["away_score"])
        actual = self.session.scalar(select(ActualResult).where(ActualResult.match_id == match.id))
        if actual and (actual.home_score != home_score or actual.away_score != away_score):
            raise ManualImportError("result_conflict")
        if actual is None:
            actual = ActualResult(match_id=match.id, home_score=home_score, away_score=away_score)
            self.session.add(actual)
        actual.result = "home_win" if home_score > away_score else "away_win" if home_score < away_score else "draw"
        actual.total_goals = home_score + away_score
        actual.btts_result = home_score > 0 and away_score > 0
        actual.completed_at = datetime.now(UTC)
        actual.result_source_id = source.id
        return 1

    def _save_standings(self, row: dict[str, Any], source: DataSource, snapshot: RawDataSnapshot, certainty: str) -> int:
        competition = self._competition(row.get("competition_code"))
        season = self._season(competition, row.get("season"), source)
        team = self._team(row, source)
        standing = self.session.scalar(select(CompetitionStanding).where(CompetitionStanding.competition_id == competition.id, CompetitionStanding.season_id == season.id, CompetitionStanding.team_id == team.id))
        if standing is None:
            standing = CompetitionStanding(competition_id=competition.id, season_id=season.id, team_id=team.id)
            self.session.add(standing)
        standing.rank = int(row["rank"]) if row.get("rank") is not None else None
        standing.points = int(row["points"]) if row.get("points") is not None else None
        standing.certainty = certainty
        standing.source_snapshot_id = snapshot.id
        return 1

    def _save_injuries(self, row: dict[str, Any], source: DataSource, snapshot: RawDataSnapshot, certainty: str) -> int:
        match = self._match(row) if row.get("match_id") else None
        player = self.session.get(Player, str(row["player_id"])) if row.get("player_id") else None
        injury = self.session.scalar(select(Injury).where(Injury.external_id == str(row.get("injury_id")), Injury.match_id == (match.id if match else None), Injury.player_id == (player.id if player else None)))
        if injury is None:
            injury = Injury(external_id=str(row.get("injury_id")) if row.get("injury_id") else None, match_id=match.id if match else None, player_id=player.id if player else None)
            self.session.add(injury)
        injury.status, injury.reason, injury.certainty, injury.source_snapshot_id = row.get("status"), row.get("reason"), certainty, snapshot.id
        return 1

    def _save_lineups(self, row: dict[str, Any], source: DataSource, snapshot: RawDataSnapshot, certainty: str) -> int:
        match = self._match(row)
        team = self.session.get(Team, str(row["team_id"]))
        if team is None:
            raise ManualImportError("team_not_found")
        lineup = MatchLineup(match_id=match.id, team_id=team.id, player_id=str(row["player_id"]) if row.get("player_id") else None, external_player_id=str(row["external_player_id"]) if row.get("external_player_id") else None, player_name=row.get("player_name"), starter=bool(row.get("starter", False)), certainty=certainty, source_snapshot_id=snapshot.id)
        self.session.add(lineup)
        match.lineup_status = "official" if certainty == "official" else "reported"
        return 1

    def _save_statistics(self, row: dict[str, Any], source: DataSource, snapshot: RawDataSnapshot, certainty: str) -> int:
        match = self._match(row)
        team = self.session.get(Team, str(row["team_id"]))
        if team is None:
            raise ManualImportError("team_not_found")
        stat = self.session.scalar(select(MatchStatistic).where(MatchStatistic.match_id == match.id, MatchStatistic.team_id == team.id))
        if stat is None:
            stat = MatchStatistic(match_id=match.id, team_id=team.id)
            self.session.add(stat)
        for field in ("shots", "shots_on_target", "possession", "corners", "xg", "xga"):
            if field in row:
                setattr(stat, field, float(row[field]) if field in {"possession", "xg", "xga"} and row[field] not in (None, "") else int(row[field]) if row[field] not in (None, "") else None)
        stat.certainty, stat.source_snapshot_id = certainty, snapshot.id
        return 1
