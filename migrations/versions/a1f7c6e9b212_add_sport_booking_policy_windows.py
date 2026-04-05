"""add sport booking policy windows

Revision ID: a1f7c6e9b212
Revises: 4f7b5c2e1d11
Create Date: 2026-04-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1f7c6e9b212"
down_revision: Union[str, Sequence[str], None] = "4f7b5c2e1d11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sports", sa.Column("booking_min_lead_minutes", sa.Integer(), nullable=True))
    op.add_column("sports", sa.Column("cancellation_min_lead_minutes", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("sports", "cancellation_min_lead_minutes")
    op.drop_column("sports", "booking_min_lead_minutes")
