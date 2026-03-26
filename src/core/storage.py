"""JSON storage utilities."""

import json
from pathlib import Path
from typing import Any


class JsonStore:
    """Persistent JSON storage."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Any | None:
        """Load data from file."""
        if not self.path.exists():
            return None
        try:
            with Path(self.path).open('r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None

    def save(self, data: Any) -> None:
        """Save data to file."""
        try:
            with Path(self.path).open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise RuntimeError(f'Failed to save {self.path}: {e}')
