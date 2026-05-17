"""
Repair SQLite colony columns when the app is newer than the DB file.

Adds missing ORM columns:
  - score_bonus
  - missions_json

Resolves the real DB path (e.g. instance/space_colony.db) via PRAGMA database_list.

From the project root:
    python scripts/ensure_colony_sqlite_columns.py

Prefer when Alembic works:
    python -m flask --app run.py db upgrade
"""
import os
import sqlite3
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]


def _resolve_sqlite_file(app) -> Optional[Path]:
    from sqlalchemy import text
    from sqlalchemy.engine.url import make_url

    url = make_url(app.config["SQLALCHEMY_DATABASE_URI"])
    if url.get_backend_name() != "sqlite":
        return None
    if not url.database or url.database == ":memory:":
        return None

    from app.extensions import db

    with app.app_context():
        with db.engine.connect() as conn:
            rows = conn.execute(text("PRAGMA database_list")).fetchall()
    for _seq, name, path in rows:
        if name == "main" and path:
            return Path(path)
    return None


def main() -> int:
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))

    from app import create_app

    app = create_app()
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    db_path = _resolve_sqlite_file(app)
    if db_path is None:
        print("Not a file-based SQLite database. URI:", uri)
        return 1
    if not db_path.is_file():
        print("Database file not found:", db_path)
        return 1

    conn = sqlite3.connect(str(db_path))
    try:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        if "colony" not in tables:
            print("No colony table in", db_path)
            return 1

        changed = False

        def colony_columns():
            return {r[1] for r in conn.execute("PRAGMA table_info(colony)").fetchall()}

        cols = colony_columns()

        if "score_bonus" not in cols:
            print("Adding colony.score_bonus …")
            conn.execute("ALTER TABLE colony ADD COLUMN score_bonus INTEGER NOT NULL DEFAULT 0")
            conn.execute(
                """
                UPDATE colony
                SET score_bonus = MAX(0, IFNULL(score, 0) - (IFNULL(total_collected, 0) / 12))
                """
            )
            conn.execute(
                """
                UPDATE colony
                SET score = (IFNULL(total_collected, 0) / 12) + IFNULL(score_bonus, 0)
                """
            )
            changed = True
            cols = colony_columns()

        if "missions_json" not in cols:
            print("Adding colony.missions_json …")
            conn.execute(
                "ALTER TABLE colony ADD COLUMN missions_json TEXT NOT NULL DEFAULT '{}'"
            )
            changed = True
            cols = colony_columns()

        if "alembic_version" in tables:
            row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
            ver = row[0] if row else None
            if ver == "c7e8f9d0g1h2" and "score_bonus" in cols:
                conn.execute(
                    "UPDATE alembic_version SET version_num = ?",
                    ("e1f2a3b4c5d6",),
                )
                print("Updated alembic_version to e1f2a3b4c5d6.")
                changed = True
                row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
                ver = row[0] if row else None
            if ver == "e1f2a3b4c5d6" and "missions_json" in cols:
                conn.execute(
                    "UPDATE alembic_version SET version_num = ?",
                    ("f2a1b2c3d4e5",),
                )
                print("Updated alembic_version to f2a1b2c3d4e5.")
                changed = True

        if changed:
            conn.commit()
            print("SQLite repair committed. Restart Flask.")
        else:
            print("Colony columns score_bonus and missions_json already present.")
        print("Database:", db_path)
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
