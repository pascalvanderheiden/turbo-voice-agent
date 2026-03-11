"""JSON file persistence for local dev — survives backend restarts."""

from __future__ import annotations

import copy
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / ".data"


class JsonPersistenceMixin:
    """Mixin that syncs an in-memory _store dict to a JSON file."""

    _store: dict[str, dict]
    _json_file: str = "data.json"
    _user_id: str | None = None

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

    def _user_items(self) -> list[dict]:
        """Return store items filtered by the current user_id (if set).

        Includes legacy items with userId='default-user' or missing userId
        so that pre-existing local-dev data keeps working after the scoping
        change.
        """
        if not self._user_id:
            return list(self._store.values())
        return [
            d for d in self._store.values()
            if d.get("userId") in (self._user_id, "default-user", None)
        ]

    def with_user(self, user_id: str):
        """Return a shallow copy of this service scoped to *user_id*."""
        scoped = copy.copy(self)
        scoped._user_id = user_id
        return scoped
