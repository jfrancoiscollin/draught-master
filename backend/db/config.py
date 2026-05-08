from __future__ import annotations
import os as _os
from pathlib import Path

_db_dir = Path(_os.getenv("DB_DIR", str(Path(__file__).parent.parent)))
_db_dir.mkdir(parents=True, exist_ok=True)
DB_PATH = _db_dir / "draught.db"
