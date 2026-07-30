from app.services.posters.schemas import PosterStyle


class StyleManager:
    _styles = {
        "CSL": PosterStyle("CSL", "csl_match_card.html", "中国超级联赛", "#E53935"),
        "MLS": PosterStyle("MLS", "mls_match_card.html", "美国职业大联盟", "#1E4ED8"),
        "LIGA_MX": PosterStyle("LIGA_MX", "liga_mx_match_card.html", "墨西哥超级联赛", "#11834A"),
        "UCL_QUALIFIER": PosterStyle("UCL_QUALIFIER", "ucl_match_card.html", "欧冠资格赛", "#1A237E"),
        "BRA_SERIE_A": PosterStyle("BRA_SERIE_A", "brasileirao_match_card.html", "巴西甲级联赛", "#F0B323"),
    }

    def get(self, competition_code: str) -> PosterStyle:
        try:
            return self._styles[competition_code.upper()]
        except KeyError as error:
            raise ValueError(f"Unsupported competition style: {competition_code}") from error

    def supported_codes(self) -> tuple[str, ...]:
        return tuple(self._styles)
