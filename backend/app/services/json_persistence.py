"""JSON file persistence for local dev — survives backend restarts."""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / ".data"


class JsonPersistenceMixin:
    """Mixin that syncs an in-memory _store dict to a JSON file."""

    _store: dict[str, dict]
    _json_file: str = "data.json"

    def _data_path(self) -> Path:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        return DATA_DIR / self._json_file

    def _load_from_disk(self) -> None:
        path = self._data_path()
        if path.exists():
            try:
                data = json.loads(path.read_text())
                self._store = data
                logger.info("Loaded %d items from %s", len(self._store), path.name)
            except Exception:
                logger.warning("Failed to load %s — starting fresh", path.name)

    def _save_to_disk(self) -> None:
        try:
            path = self._data_path()
            path.write_text(json.dumps(self._store, default=str, indent=2))
        except Exception:
            logger.warning("Failed to save %s", self._json_file)
