"""add org settings and staff invitations

Revision ID: f1b2c3d4e5f6
Revises: e6a3c9f4b8d1
Create Date: 2026-04-02 03:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "e6a3c9f4b8d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organization_settings",
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("branding_name", sa.String(length=150), nullable=True),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("primary_color", sa.String(length=32), nullable=True),
        sa.Column("booking_min_lead_minutes", sa.Integer(), nullable=True),
        sa.Column("cancellation_min_lead_minutes", sa.Integer(), nullable=True),
        sa.Column("whatsapp_provider", sa.String(length=50), nullable=True),
        sa.Column("whatsapp_access_token", sa.String(length=500), nullable=True),
        sa.Column("whatsapp_phone_number_id", sa.String(length=100), nullable=True),
        sa.Column("whatsapp_template_language", sa.String(length=20), nullable=True),
        sa.Column("whatsapp_template_booking_confirmed", sa.String(length=150), nullable=True),
        sa.Column("whatsapp_template_booking_cancelled", sa.String(length=150), nullable=True),
        sa.Column("whatsapp_recipient_override", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("organization_id"),
    )

    op.create_table(
        "staff_invitations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("invited_by_user_id", sa.UUID(), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=20), server_default="user", nullable=False),
        sa.Column("invite_token", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_staff_invitations_email"), "staff_invitations", ["email"], unique=False)
    op.create_index(op.f("ix_staff_invitations_invite_token"), "staff_invitations", ["invite_token"], unique=True)
    op.create_index(op.f("ix_staff_invitations_organization_id"), "staff_invitations", ["organization_id"], unique=False)

    op.execute(
        """
        INSERT INTO organization_settings (organization_id, branding_name)
        SELECT id, name
        FROM organizations
        ON CONFLICT (organization_id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_staff_invitations_organization_id"), table_name="staff_invitations")
    op.drop_index(op.f("ix_staff_invitations_invite_token"), table_name="staff_invitations")
    op.drop_index(op.f("ix_staff_invitations_email"), table_name="staff_invitations")
    op.drop_table("staff_invitations")
    op.drop_table("organization_settings")
