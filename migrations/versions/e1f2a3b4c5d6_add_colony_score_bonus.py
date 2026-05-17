"""Add score_bonus to colony for extraction-based score

Revision ID: e1f2a3b4c5d6
Revises: c7e8f9d0g1h2
Create Date: 2026-05-17 12:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

revision = "e1f2a3b4c5d6"
down_revision = "c7e8f9d0g1h2"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    existing = {row[1] for row in conn.execute(sa.text("PRAGMA table_info(colony)"))}
    if "score_bonus" not in existing:
        with op.batch_alter_table("colony", schema=None) as batch_op:
            batch_op.add_column(sa.Column("score_bonus", sa.Integer(), server_default="0", nullable=False))
    rows = conn.execute(sa.text("SELECT id, score, total_collected FROM colony")).fetchall()
    for cid, score, total_collected in rows:
        total = int(total_collected or 0)
        extraction_score = total // 12
        bonus = max(0, int(score or 0) - extraction_score)
        new_score = extraction_score + bonus
        conn.execute(
            sa.text("UPDATE colony SET score_bonus = :bonus, score = :score WHERE id = :id"),
            {"bonus": bonus, "score": new_score, "id": cid},
        )


def downgrade():
    conn = op.get_bind()
    existing = {row[1] for row in conn.execute(sa.text("PRAGMA table_info(colony)"))}
    if "score_bonus" in existing:
        with op.batch_alter_table("colony", schema=None) as batch_op:
            batch_op.drop_column("score_bonus")
