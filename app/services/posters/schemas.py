from dataclasses import dataclass


@dataclass(frozen=True)
class PosterStyle:
    code: str
    template_name: str
    display_name: str
    accent_color: str
    template_version: str = "v1"


@dataclass(frozen=True)
class PosterData:
    competition_name: str
    beijing_time: str
    home_team: str
    away_team: str
    direction: str
    goal_range: str
    btts_tendency: str
    primary_score: str
    stable_score: str
    alternative_score: str
    risk_level: str
    confidence: str
    watermark: str
    accent_color: str


@dataclass(frozen=True)
class RenderedPoster:
    file_path: str
    image_url: str
    model_version: str | None = None
    feature_version: str | None = None
    data_version: str | None = None
    prompt_version: str | None = None
    poster_version: str | None = None
