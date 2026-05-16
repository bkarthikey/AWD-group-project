"""Add thanks message to reward exchange

Revision ID: b9f4d9d8f4c1
Revises: 4fd0dcf7bf32
Create Date: 2026-05-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "b9f4d9d8f4c1"
down_revision = "4fd0dcf7bf32"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("reward_exchange", schema=None) as batch_op:
        batch_op.add_column(sa.Column("thanks_message", sa.String(length=240), nullable=True))


def downgrade():
    with op.batch_alter_table("reward_exchange", schema=None) as batch_op:
        batch_op.drop_column("thanks_message")
