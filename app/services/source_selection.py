"""Deterministic source selection without upgrading certainty."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class SourceFact:
    value: object
    source_type: str
    certainty: str
    retrieved_at: datetime
    match_id: str | None = None
    expires_after: timedelta | None = None


class SourceSelector:
    _certainty_rank = {"official": 5, "confirmed": 4, "reported": 3, "predicted": 2, "unavailable": 0}
    _source_rank = {"official_manual": 5, "api_football": 4, "trusted_open_data": 3, "existing_database": 2, "unavailable": 0}

    @classmethod
    def choose(cls, facts: list[SourceFact], *, match_id: str | None = None, now: datetime | None = None) -> tuple[SourceFact | None, bool]:
        now = now or datetime.now(UTC)
        candidates = [fact for fact in facts if (match_id is None or fact.match_id in {None, match_id}) and cls._fresh(fact, now)]
        if not candidates:
            return None, False
        candidates.sort(key=lambda fact: (cls._certainty_rank.get(fact.certainty, 0), cls._source_rank.get(fact.source_type, 0), fact.retrieved_at), reverse=True)
        top = candidates[0]
        conflict = any(fact.value != top.value for fact in candidates[1:])
        return top, conflict

    @staticmethod
    def _fresh(fact: SourceFact, now: datetime) -> bool:
        if fact.expires_after is None:
            return True
        return now - fact.retrieved_at <= fact.expires_after
