"""Add exchange type to reward exchange

Revision ID: 4fd0dcf7bf32
Revises: 090517857f22
Create Date: 2026-05-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "4fd0dcf7bf32"
down_revision = "090517857f22"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("reward_exchange", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("exchange_type", sa.String(length=20), server_default="offer", nullable=False)
        )


def downgrade():
    with op.batch_alter_table("reward_exchange", schema=None) as batch_op:
        batch_op.drop_column("exchange_type")
