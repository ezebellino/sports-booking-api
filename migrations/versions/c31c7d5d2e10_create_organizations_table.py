"""create organizations table

Revision ID: c31c7d5d2e10
Revises: b92d4a1f8c44
Create Date: 2026-04-02 00:00:00.000000

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "c31c7d5d2e10"
down_revision: Union[str, Sequence[str], None] = "b92d4a1f8c44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


organizations_table = sa.table(
    "organizations",
    sa.column("id", sa.UUID()),
    sa.column("name", sa.String(length=150)),
    sa.column("slug", sa.String(length=150)),
    sa.column("is_active", sa.Boolean()),
)


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("slug", sa.String(length=150), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_organizations_name"), "organizations", ["name"], unique=False)
    op.create_index(op.f("ix_organizations_slug"), "organizations", ["slug"], unique=True)

    op.bulk_insert(
        organizations_table,
        [
            {
                "id": uuid.uuid4(),
                "name": "Complejo Demo",
                "slug": "complejo-demo",
                "is_active": True,
            }
        ],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_organizations_slug"), table_name="organizations")
    op.drop_index(op.f("ix_organizations_name"), table_name="organizations")
    op.drop_table("organizations")
