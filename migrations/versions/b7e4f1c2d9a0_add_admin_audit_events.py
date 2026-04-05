"""add admin audit events

Revision ID: b7e4f1c2d9a0
Revises: a8d4e1b7c2f3
Create Date: 2026-04-05 21:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7e4f1c2d9a0"
down_revision: Union[str, Sequence[str], None] = "a8d4e1b7c2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admin_audit_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("target_type", sa.String(length=80), nullable=False),
        sa.Column("target_id", sa.String(length=80), nullable=True),
        sa.Column("summary", sa.String(length=255), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_admin_audit_events_action"), "admin_audit_events", ["action"], unique=False)
    op.create_index(op.f("ix_admin_audit_events_actor_user_id"), "admin_audit_events", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_admin_audit_events_created_at"), "admin_audit_events", ["created_at"], unique=False)
    op.create_index(op.f("ix_admin_audit_events_organization_id"), "admin_audit_events", ["organization_id"], unique=False)
    op.create_index(op.f("ix_admin_audit_events_target_type"), "admin_audit_events", ["target_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_admin_audit_events_target_type"), table_name="admin_audit_events")
    op.drop_index(op.f("ix_admin_audit_events_organization_id"), table_name="admin_audit_events")
    op.drop_index(op.f("ix_admin_audit_events_created_at"), table_name="admin_audit_events")
    op.drop_index(op.f("ix_admin_audit_events_actor_user_id"), table_name="admin_audit_events")
    op.drop_index(op.f("ix_admin_audit_events_action"), table_name="admin_audit_events")
    op.drop_table("admin_audit_events")
