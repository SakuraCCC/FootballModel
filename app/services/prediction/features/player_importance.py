from app.models import PlayerImportanceScore

POSITION_WEIGHTS = {"goalkeeper": 0.8, "defender": 0.9, "midfielder": 1.0, "forward": 1.15}


def calculate_player_importance(
    *, minutes_played: int | None, goals: int | None, assists: int | None, position: str | None
) -> tuple[float | None, float | None]:
    """Return a transparent provider-fact score, or unavailable when minutes are absent."""
    if minutes_played is None:
        return None, None
    weight = POSITION_WEIGHTS.get((position or "").lower(), 1.0)
    score = (minutes_played / 90 + (goals or 0) * 4 + (assists or 0) * 3) * weight
    return round(score, 4), weight


def refresh_player_importance(record: PlayerImportanceScore) -> PlayerImportanceScore:
    record.score, record.position_weight = calculate_player_importance(
        minutes_played=record.minutes_played,
        goals=record.goals,
        assists=record.assists,
        position=record.position,
    )
    return record
