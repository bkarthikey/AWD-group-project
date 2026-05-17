"""
Deprecated name: repairs SQLite colony columns (score_bonus, missions_json).

Use: python scripts/ensure_colony_sqlite_columns.py
"""
import importlib.util
from pathlib import Path

_path = Path(__file__).resolve().parent / "ensure_colony_sqlite_columns.py"
_spec = importlib.util.spec_from_file_location("ensure_colony_sqlite_columns", _path)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader
_spec.loader.exec_module(_mod)

if __name__ == "__main__":
    raise SystemExit(_mod.main())
