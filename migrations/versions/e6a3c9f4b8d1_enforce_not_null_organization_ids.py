"""enforce not null organization ids

Revision ID: e6a3c9f4b8d1
Revises: d9f6a3a4b1e2
Create Date: 2026-04-02 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e6a3c9f4b8d1"
down_revision: Union[str, Sequence[str], None] = "d9f6a3a4b1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _scalar(connection, sql: str):
    return connection.execute(sa.text(sql)).scalar_one()


def _ensure_zero(connection, sql: str, label: str) -> None:
    value = int(_scalar(connection, sql))
    if value != 0:
        raise RuntimeError(f"No se puede endurecer organization_id: {label} ({value})")


def upgrade() -> None:
    connection = op.get_bind()
    default_org_id = _scalar(
        connection,
        "SELECT id FROM organizations WHERE slug = 'complejo-demo' LIMIT 1",
    )
    if not default_org_id:
        raise RuntimeError("No se encontró la organización por defecto 'complejo-demo'")

    connection.execute(
        sa.text(
            """
            UPDATE users
            SET organization_id = :default_org_id
            WHERE organization_id IS NULL
            """
        ),
        {"default_org_id": default_org_id},
    )
    connection.execute(
        sa.text(
            """
            UPDATE venues
            SET organization_id = :default_org_id
            WHERE organization_id IS NULL
            """
        ),
        {"default_org_id": default_org_id},
    )
    connection.execute(
        sa.text(
            """
            UPDATE courts
            SET organization_id = COALESCE(
                (
                    SELECT venues.organization_id
                    FROM venues
                    WHERE venues.id = courts.venue_id
                ),
                :default_org_id
            )
            WHERE organization_id IS NULL
            """
        ),
        {"default_org_id": default_org_id},
    )
    connection.execute(
        sa.text(
            """
            UPDATE timeslots
            SET organization_id = COALESCE(
                (
                    SELECT courts.organization_id
                    FROM courts
                    WHERE courts.id = timeslots.court_id
                ),
                :default_org_id
            )
            WHERE organization_id IS NULL
            """
        ),
        {"default_org_id": default_org_id},
    )
    connection.execute(
        sa.text(
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
                :default_org_id
            )
            WHERE organization_id IS NULL
            """
        ),
        {"default_org_id": default_org_id},
    )

    _ensure_zero(connection, "SELECT COUNT(*) FROM users WHERE organization_id IS NULL", "usuarios sin organización")
    _ensure_zero(connection, "SELECT COUNT(*) FROM venues WHERE organization_id IS NULL", "sedes sin organización")
    _ensure_zero(connection, "SELECT COUNT(*) FROM courts WHERE organization_id IS NULL", "canchas sin organización")
    _ensure_zero(connection, "SELECT COUNT(*) FROM timeslots WHERE organization_id IS NULL", "turnos sin organización")
    _ensure_zero(connection, "SELECT COUNT(*) FROM bookings WHERE organization_id IS NULL", "reservas sin organización")

    _ensure_zero(
        connection,
        """
        SELECT COUNT(*)
        FROM courts
        JOIN venues ON venues.id = courts.venue_id
        WHERE courts.organization_id <> venues.organization_id
        """,
        "canchas ligadas a una sede de otra organización",
    )
    _ensure_zero(
        connection,
        """
        SELECT COUNT(*)
        FROM timeslots
        JOIN courts ON courts.id = timeslots.court_id
        WHERE timeslots.organization_id <> courts.organization_id
        """,
        "turnos ligados a una cancha de otra organización",
    )
    _ensure_zero(
        connection,
        """
        SELECT COUNT(*)
        FROM bookings
        JOIN users ON users.id = bookings.user_id
        WHERE bookings.organization_id <> users.organization_id
        """,
        "reservas ligadas a un usuario de otra organización",
    )
    _ensure_zero(
        connection,
        """
        SELECT COUNT(*)
        FROM bookings
        JOIN timeslots ON timeslots.id = bookings.timeslot_id
        WHERE bookings.organization_id <> timeslots.organization_id
        """,
        "reservas ligadas a un turno de otra organización",
    )

    op.alter_column("users", "organization_id", existing_type=sa.UUID(), nullable=False)
    op.alter_column("venues", "organization_id", existing_type=sa.UUID(), nullable=False)
    op.alter_column("courts", "organization_id", existing_type=sa.UUID(), nullable=False)
    op.alter_column("timeslots", "organization_id", existing_type=sa.UUID(), nullable=False)
    op.alter_column("bookings", "organization_id", existing_type=sa.UUID(), nullable=False)


def downgrade() -> None:
    op.alter_column("bookings", "organization_id", existing_type=sa.UUID(), nullable=True)
    op.alter_column("timeslots", "organization_id", existing_type=sa.UUID(), nullable=True)
    op.alter_column("courts", "organization_id", existing_type=sa.UUID(), nullable=True)
    op.alter_column("venues", "organization_id", existing_type=sa.UUID(), nullable=True)
    op.alter_column("users", "organization_id", existing_type=sa.UUID(), nullable=True)
