"""add whatsapp fields to users

Revision ID: b92d4a1f8c44
Revises: a1f7c6e9b212
Create Date: 2026-04-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b92d4a1f8c44"
down_revision: Union[str, Sequence[str], None] = "a1f7c6e9b212"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("whatsapp_number", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("whatsapp_opt_in", sa.Boolean(), nullable=False, server_default=sa.text("false")))


def downgrade() -> None:
    op.drop_column("users", "whatsapp_opt_in")
    op.drop_column("users", "whatsapp_number")
