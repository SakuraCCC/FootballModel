import re
import unicodedata

TEAM_ALIASES = {
    "paris sg": "Paris Saint-Germain",
    "paris saint germain": "Paris Saint-Germain",
    "psg": "Paris Saint-Germain",
}


def normalized_key(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_marks = "".join(character for character in decomposed if not unicodedata.combining(character))
    return re.sub(r"[^a-z0-9]+", " ", without_marks.casefold()).strip()


def canonical_team_name(value: str) -> str:
    key = normalized_key(value)
    return TEAM_ALIASES.get(key, value.strip())
