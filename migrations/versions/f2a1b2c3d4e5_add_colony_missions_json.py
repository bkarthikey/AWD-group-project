"""Add colony.missions_json for server-tracked harvest directives."""

import sqlalchemy as sa
from alembic import op

revision = "f2a1b2c3d4e5"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    cols = {row[1] for row in conn.execute(sa.text("PRAGMA table_info(colony)"))}
    if "missions_json" not in cols:
        with op.batch_alter_table("colony", schema=None) as batch_op:
            batch_op.add_column(sa.Column("missions_json", sa.Text(), server_default="{}", nullable=False))


def downgrade():
    conn = op.get_bind()
    cols = {row[1] for row in conn.execute(sa.text("PRAGMA table_info(colony)"))}
    if "missions_json" in cols:
        with op.batch_alter_table("colony", schema=None) as batch_op:
            batch_op.drop_column("missions_json")
