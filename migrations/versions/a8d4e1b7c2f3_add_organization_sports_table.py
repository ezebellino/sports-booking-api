"""add organization sports table

Revision ID: a8d4e1b7c2f3
Revises: f1b2c3d4e5f6
Create Date: 2026-04-04 13:40:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "a8d4e1b7c2f3"
down_revision = "f1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organization_sports",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sport_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sport_id"], ["sports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("organization_id", "sport_id"),
    )

    op.execute(
        """
        INSERT INTO organization_sports (organization_id, sport_id, is_enabled)
        SELECT organizations.id, sports.id, true
        FROM organizations
        CROSS JOIN sports
        """
    )


def downgrade() -> None:
    op.drop_table("organization_sports")
