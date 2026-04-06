"""add organization memberships

Revision ID: f3c4b8a1d2e7
Revises: b7e4f1c2d9a0
Create Date: 2026-04-06 00:00:00.000000
"""

from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "f3c4b8a1d2e7"
down_revision: Union[str, Sequence[str], None] = "b7e4f1c2d9a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organization_memberships",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="user"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "organization_id", name="uq_organization_memberships_user_org"),
    )
    op.create_index(op.f("ix_organization_memberships_user_id"), "organization_memberships", ["user_id"], unique=False)
    op.create_index(op.f("ix_organization_memberships_organization_id"), "organization_memberships", ["organization_id"], unique=False)
    op.create_index(op.f("ix_organization_memberships_role"), "organization_memberships", ["role"], unique=False)

    connection = op.get_bind()
    users = connection.execute(
        sa.text(
            """
            SELECT id, organization_id, role
            FROM users
            WHERE organization_id IS NOT NULL
            """
        )
    ).mappings().all()

    if users:
        membership_table = sa.table(
            "organization_memberships",
            sa.column("id", sa.UUID()),
            sa.column("user_id", sa.UUID()),
            sa.column("organization_id", sa.UUID()),
            sa.column("role", sa.String(length=20)),
            sa.column("is_default", sa.Boolean()),
            sa.column("created_at", sa.DateTime(timezone=True)),
            sa.column("updated_at", sa.DateTime(timezone=True)),
        )
        now = connection.execute(sa.select(sa.func.now())).scalar_one()
        op.bulk_insert(
            membership_table,
            [
                {
                    "id": uuid.uuid4(),
                    "user_id": user["id"],
                    "organization_id": user["organization_id"],
                    "role": user["role"],
                    "is_default": True,
                    "created_at": now,
                    "updated_at": now,
                }
                for user in users
            ],
        )


def downgrade() -> None:
    op.drop_index(op.f("ix_organization_memberships_role"), table_name="organization_memberships")
    op.drop_index(op.f("ix_organization_memberships_organization_id"), table_name="organization_memberships")
    op.drop_index(op.f("ix_organization_memberships_user_id"), table_name="organization_memberships")
    op.drop_table("organization_memberships")
