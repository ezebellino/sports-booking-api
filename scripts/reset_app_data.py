from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import delete, inspect

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.organization_settings import get_or_create_organization_settings
from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.booking import Booking
from app.models.court import Court
from app.models.organization import Organization
from app.models.organization_settings import OrganizationSettings
from app.models.sport import Sport
from app.models.staff_invitation import StaffInvitation
from app.models.timeslot import TimeSlot
from app.models.user import User
from app.models.venue import Venue


DEFAULT_ADMIN_EMAIL = "admin@sportsbooking.com"
DEFAULT_ADMIN_PASSWORD = "SportsBooking123!"
DEFAULT_ORGANIZATION_NAME = "Sports Booking Demo"
DEFAULT_ORGANIZATION_SLUG = "complejo-demo"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Borra los datos operativos y recrea un admin base para arrancar desde cero.",
    )
    parser.add_argument("--admin-email", default=DEFAULT_ADMIN_EMAIL)
    parser.add_argument("--admin-password", default=DEFAULT_ADMIN_PASSWORD)
    parser.add_argument("--admin-name", default="Administrador Sports Booking")
    parser.add_argument("--organization-name", default=DEFAULT_ORGANIZATION_NAME)
    parser.add_argument("--organization-slug", default=DEFAULT_ORGANIZATION_SLUG)
    return parser


def reset_app_data() -> None:
    args = build_parser().parse_args()
    session = SessionLocal()
    try:
        existing_tables = set(inspect(session.bind).get_table_names())

        for model in (
            Booking,
            TimeSlot,
            Court,
            Venue,
            StaffInvitation,
            OrganizationSettings,
            User,
            Organization,
            Sport,
        ):
            if model.__tablename__ in existing_tables:
                session.execute(delete(model))

        organization = Organization(
            name=args.organization_name,
            slug=args.organization_slug,
            is_active=True,
        )
        session.add(organization)
        session.flush()

        if OrganizationSettings.__tablename__ in existing_tables:
            settings = get_or_create_organization_settings(session, organization)
            settings.branding_name = args.organization_name
            session.add(settings)
            session.flush()

        admin_user = User(
            email=args.admin_email,
            full_name=args.admin_name,
            hashed_password=get_password_hash(args.admin_password),
            role="admin",
            organization_id=organization.id,
            whatsapp_opt_in=False,
        )
        session.add(admin_user)
        session.commit()

        print("Reset completado.")
        print(f"Complejo base: {args.organization_name} ({args.organization_slug})")
        print(f"Admin base: {args.admin_email}")
        print(f"Password base: {args.admin_password}")
    finally:
        session.close()


if __name__ == "__main__":
    reset_app_data()
