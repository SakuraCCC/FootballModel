from dataclasses import dataclass
from typing import Any

from app.services.normalization.names import normalized_key


@dataclass(frozen=True)
class NormalizedPlayer:
    external_id: str | None
    canonical_name: str | None
    normalized_name: str | None
    certainty: str = "reported"


def normalize_player(payload: dict[str, Any]) -> NormalizedPlayer:
    player = payload.get("player", payload)
    raw_name = player.get("name") if isinstance(player, dict) else None
    name = raw_name.strip() if isinstance(raw_name, str) and raw_name.strip() else None
    return NormalizedPlayer(
        external_id=str(player["id"]) if isinstance(player, dict) and player.get("id") is not None else None,
        canonical_name=name,
        normalized_name=normalized_key(name) if name else None,
    )
