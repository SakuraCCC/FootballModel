"""Data quality checks for normalized facts."""

from app.services.quality.completeness import MatchCompleteness, assess_match_completeness

__all__ = ["MatchCompleteness", "assess_match_completeness"]
