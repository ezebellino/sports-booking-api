"""add organization id to core tables

Revision ID: d9f6a3a4b1e2
Revises: c31c7d5d2e10
Create Date: 2026-04-02 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d9f6a3a4b1e2"
down_revision: Union[str, Sequence[str], None] = "c31c7d5d2e10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("organization_id", sa.UUID(), nullable=True))
    op.add_column("venues", sa.Column("organization_id", sa.UUID(), nullable=True))
    op.add_column("courts", sa.Column("organization_id", sa.UUID(), nullable=True))
    op.add_column("timeslots", sa.Column("organization_id", sa.UUID(), nullable=True))
    op.add_column("bookings", sa.Column("organization_id", sa.UUID(), nullable=True))

    op.create_index(op.f("ix_users_organization_id"), "users", ["organization_id"], unique=False)
    op.create_index(op.f("ix_venues_organization_id"), "venues", ["organization_id"], unique=False)
    op.create_index(op.f("ix_courts_organization_id"), "courts", ["organization_id"], unique=False)
    op.create_index(op.f("ix_timeslots_organization_id"), "timeslots", ["organization_id"], unique=False)
    op.create_index(op.f("ix_bookings_organization_id"), "bookings", ["organization_id"], unique=False)

    op.create_foreign_key("fk_users_organization_id", "users", "organizations", ["organization_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_venues_organization_id", "venues", "organizations", ["organization_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_courts_organization_id", "courts", "organizations", ["organization_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_timeslots_organization_id", "timeslots", "organizations", ["organization_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_bookings_organization_id", "bookings", "organizations", ["organization_id"], ["id"], ondelete="SET NULL")

    op.execute(
        """
        UPDATE users
        SET organization_id = (
            SELECT id FROM organizations WHERE slug = 'complejo-demo' LIMIT 1
        )
        WHERE organization_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE venues
        SET organization_id = (
            SELECT id FROM organizations WHERE slug = 'complejo-demo' LIMIT 1
        )
        WHERE organization_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE courts
        SET organization_id = COALESCE(
            (
                SELECT venues.organization_id
                FROM venues
                WHERE venues.id = courts.venue_id
            ),
            (
                SELECT id FROM organizations WHERE slug = 'complejo-demo' LIMIT 1
            )
        )
        WHERE organization_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE timeslots
        SET organization_id = COALESCE(
            (
                SELECT courts.organization_id
                FROM courts
                WHERE courts.id = timeslots.court_id
            ),
            (
                SELECT id FROM organizations WHERE slug = 'complejo-demo' LIMIT 1
            )
        )
        WHERE organization_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE bookings
        SET organization_id = COALESCE(
            (
                SELECT timeslots.organization_id
                FROM timeslots
                WHERE timeslots.id = bookings.timeslot_id
            ),
            (
                SELECT users.organization_id
                FROM users
                WHERE users.id = bookings.user_id
            ),
            (
                SELECT id FROM organizations WHERE slug = 'complejo-demo' LIMIT 1
            )
        )
        WHERE organization_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_constraint("fk_bookings_organization_id", "bookings", type_="foreignkey")
    op.drop_constraint("fk_timeslots_organization_id", "timeslots", type_="foreignkey")
    op.drop_constraint("fk_courts_organization_id", "courts", type_="foreignkey")
    op.drop_constraint("fk_venues_organization_id", "venues", type_="foreignkey")
    op.drop_constraint("fk_users_organization_id", "users", type_="foreignkey")

    op.drop_index(op.f("ix_bookings_organization_id"), table_name="bookings")
    op.drop_index(op.f("ix_timeslots_organization_id"), table_name="timeslots")
    op.drop_index(op.f("ix_courts_organization_id"), table_name="courts")
    op.drop_index(op.f("ix_venues_organization_id"), table_name="venues")
    op.drop_index(op.f("ix_users_organization_id"), table_name="users")

    op.drop_column("bookings", "organization_id")
    op.drop_column("timeslots", "organization_id")
    op.drop_column("courts", "organization_id")
    op.drop_column("venues", "organization_id")
    op.drop_column("users", "organization_id")
