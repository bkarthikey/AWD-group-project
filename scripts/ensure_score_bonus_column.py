"""
One-time repair: add colony.score_bonus if the DB predates that migration.

Use when you see: OperationalError: no such column: colony.score_bonus

From the project root:
    python scripts/ensure_score_bonus_column.py

Flask-SQLAlchemy stores relative paths like sqlite:///space_colony.db under
instance/space_colony.db — this script resolves the real file via PRAGMA.

When Alembic has no version row but tables exist, prefer:
    python -m flask --app run.py db stamp c7e8f9d0g1h2
    python -m flask --app run.py db upgrade
"""
import os
import sqlite3
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]


def _resolve_sqlite_file(app) -> Optional[Path]:
    """Path to the on-disk SQLite file (same as Flask-Migrate uses)."""
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
        print("Not a file-based SQLite database; fix migrations manually. URI:", uri)
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

        cols = {r[1] for r in conn.execute("PRAGMA table_info(colony)").fetchall()}
        if "score_bonus" in cols:
            print("colony.score_bonus already exists - nothing to do.")
            print("Database:", db_path)
            return 0

        print("Adding colony.score_bonus and backfilling scores …")
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

        if "alembic_version" in tables:
            row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
            if row and row[0] == "c7e8f9d0g1h2":
                conn.execute(
                    "UPDATE alembic_version SET version_num = ?",
                    ("e1f2a3b4c5d6",),
                )
                print("Updated alembic_version to e1f2a3b4c5d6 (add colony score_bonus).")

        conn.commit()
        print("Done. Restart the Flask app and reload the dashboard.")
        print("Database:", db_path)
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
