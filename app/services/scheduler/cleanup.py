from datetime import UTC, datetime, timedelta
from pathlib import Path


class TemporaryFileCleaner:
    def __init__(self, directory: str | Path) -> None:
        self._directory = Path(directory)

    def remove_expired(self, *, now: datetime | None = None, max_age_hours: int = 24) -> int:
        if not self._directory.exists():
            return 0
        cutoff = (now or datetime.now(UTC)) - timedelta(hours=max_age_hours)
        removed = 0
        for path in self._directory.iterdir():
            if path.is_file() and datetime.fromtimestamp(path.stat().st_mtime, UTC) < cutoff:
                path.unlink()
                removed += 1
        return removed
