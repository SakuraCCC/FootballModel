from datetime import UTC
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Competition, Match, PosterOutput, PredictionResult, ReportOutput, Team
from app.services.posters.renderer import PosterRenderer
from app.services.posters.schemas import PosterData, PosterStyle, RenderedPoster
from app.services.posters.style_manager import StyleManager
from app.services.posters.watermark import watermark_text


class PosterService:
    def __init__(
        self,
        session: Session,
        *,
        renderer: PosterRenderer | None = None,
        style_manager: StyleManager | None = None,
    ) -> None:
        self._session = session
        self._renderer = renderer or PosterRenderer(output_directory=get_settings().poster_output_dir)
        self._style_manager = style_manager or StyleManager()

    def generate(self, report_id: str) -> RenderedPoster:
        report = self._session.get(ReportOutput, report_id)
        if report is None:
            raise ValueError("Report was not found")
        if report.status != "generated" or report.review_status not in {"fact_checked", "approved"}:
            raise ValueError("Only fact-checked generated reports can produce posters")
        prediction = self._session.get(PredictionResult, report.prediction_id)
        if prediction is None:
            raise ValueError("Report prediction was not found")
        match = self._session.get(Match, prediction.match_id)
        if match is None:
            raise ValueError("Prediction match was not found")
        competition = self._session.get(Competition, match.competition_id)
        if competition is None:
            raise ValueError("Match competition was not found")
        style = self._style_manager.get(competition.code)
        poster = PosterOutput(
            report_id=report.id,
            prediction_id=prediction.id,
            competition_style=style.code,
            file_path="",
            template_version=style.template_version,
            review_status="approved" if report.review_status == "approved" else "fact_checked",
        )
        self._session.add(poster)
        self._session.flush()
        try:
            file_path = self._renderer.render(
                poster.id, style, self._poster_data(match, competition, prediction, style)
            )
        except Exception:
            self._session.rollback()
            raise
        poster.file_path = str(file_path)
        self._session.commit()
        self._session.refresh(poster)
        return self._to_rendered(poster)

    def get(self, poster_id: str) -> RenderedPoster:
        poster = self._session.get(PosterOutput, poster_id)
        if poster is None:
            raise ValueError("Poster was not found")
        return self._to_rendered(poster)

    def _poster_data(
        self,
        match: Match,
        competition: Competition,
        prediction: PredictionResult,
        style: PosterStyle,
    ) -> PosterData:
        home = self._session.get(Team, match.home_team_id) if match.home_team_id else None
        away = self._session.get(Team, match.away_team_id) if match.away_team_id else None
        return PosterData(
            competition_name=competition.name,
            beijing_time=self._beijing_time(match.kickoff_at),
            home_team=home.canonical_name if home else "未提供",
            away_team=away.canonical_name if away else "未提供",
            direction=prediction.direction or "模型结果不可用",
            goal_range=prediction.goal_range or "未提供",
            btts_tendency={"likely": "倾向双方均进球", "unlikely": "倾向至少一方不进球"}.get(
                prediction.btts, "未提供"
            ),
            primary_score=prediction.primary_score or "未提供",
            stable_score=prediction.stable_score or "未提供",
            alternative_score=prediction.alternative_score or "未提供",
            risk_level={"high": "低", "medium": "中", "low": "高"}.get(prediction.confidence, "高"),
            confidence=prediction.confidence,
            watermark=watermark_text(),
            accent_color=style.accent_color,
        )

    @staticmethod
    def _beijing_time(kickoff_at) -> str:
        if kickoff_at is None:
            return "未提供"
        timestamp = kickoff_at if kickoff_at.tzinfo else kickoff_at.replace(tzinfo=UTC)
        return timestamp.astimezone(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M")

    @staticmethod
    def _to_rendered(poster: PosterOutput) -> RenderedPoster:
        return RenderedPoster(
            file_path=poster.file_path,
            image_url=f"/generated/posters/{Path(poster.file_path).name}",
        )
