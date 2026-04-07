from datetime import datetime, timedelta, timezone

from app.core.holidays import HolidayProviderError, HolidayRecord
from app.core.organization_memberships import ensure_membership
from app.models.admin_audit_event import AdminAuditEvent
from app.core.security import get_password_hash
from app.models.booking import Booking
from app.models.court import Court
from app.models.organization import Organization
from app.models.organization_membership import OrganizationMembership
from app.models.organization_settings import OrganizationSettings
from app.models.sport import Sport
from app.models.staff_invitation import StaffInvitation
from app.models.timeslot import TimeSlot
from app.models.user import User
from app.models.venue import Venue


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register_and_login(client, email: str, password: str, full_name: str = "Test User") -> str:
    register_response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": full_name,
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


def onboard_organization(
    client,
    *,
    organization_name: str,
    admin_email: str,
    admin_full_name: str = "Owner Admin",
    organization_slug: str | None = None,
    admin_password: str = "password123",
):
    payload = {
        "organization_name": organization_name,
        "admin_full_name": admin_full_name,
        "admin_email": admin_email,
        "admin_password": admin_password,
    }
    if organization_slug:
        payload["organization_slug"] = organization_slug

    response = client.post("/organizations/onboard", json=payload)
    assert response.status_code == 201
    return response.json()


def get_default_organization(db_session) -> Organization:
    organization = db_session.query(Organization).filter(Organization.slug == "complejo-demo").first()
    if organization:
        return organization

    organization = Organization(name="Complejo Demo", slug="complejo-demo", is_active=True)
    db_session.add(organization)
    db_session.commit()
    db_session.refresh(organization)
    return organization


def seed_timeslot(db_session, *, capacity: int = 1) -> TimeSlot:
    organization = get_default_organization(db_session)
    sport = Sport(name="Padel", description="Partidos rápidos")
    db_session.add(sport)
    db_session.flush()

    venue = Venue(
        name="Complejo Norte",
        address="Av. Siempre Viva 123",
        timezone="America/Argentina/Buenos_Aires",
        allowed_sport_id=sport.id,
        organization_id=organization.id,
    )
    db_session.add(venue)
    db_session.flush()

    court = Court(
        venue_id=venue.id,
        sport_id=sport.id,
        name="Cancha 1",
        indoor=True,
        is_active=True,
        organization_id=organization.id,
    )
    db_session.add(court)
    db_session.flush()

    starts_at = datetime.now(timezone.utc) + timedelta(days=1)
    timeslot = TimeSlot(
        court_id=court.id,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1, minutes=30),
        capacity=capacity,
        price=12000,
        is_active=True,
        organization_id=organization.id,
    )
    db_session.add(timeslot)
    db_session.commit()
    db_session.refresh(timeslot)
    return timeslot


def test_register_login_me_and_refresh_flow(client):
    email = "player@example.com"
    password = "password123"

    register_response = client.post(
        "/auth/register",
        json={"email": email, "password": password, "full_name": "Player One"},
    )

    assert register_response.status_code == 201
    assert register_response.json()["email"] == email
    assert register_response.json()["role"] == "user"

    login_response = client.post("/auth/login", data={"username": email, "password": password})
    assert login_response.status_code == 200

    tokens = login_response.json()
    assert tokens["access_token"]
    assert tokens["refresh_token"]
    assert tokens["token_type"] == "bearer"

    me_response = client.get("/auth/me", headers=auth_headers(tokens["access_token"]))
    assert me_response.status_code == 200
    assert me_response.json()["full_name"] == "Player One"
    assert me_response.json()["role"] == "user"
    assert me_response.json()["organization_slug"] == "complejo-demo"

    refresh_response = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh_response.status_code == 200
    assert refresh_response.json()["access_token"]
    assert refresh_response.json()["refresh_token"]


def test_register_assigns_default_organization(client, db_session):
    organization = get_default_organization(db_session)

    register_response = client.post(
        "/auth/register",
        json={"email": "legacy@example.com", "password": "password123", "full_name": "Legacy User"},
    )
    assert register_response.status_code == 201

    created_user = db_session.query(User).filter(User.email == "legacy@example.com").first()
    assert created_user is not None
    assert created_user.organization_id == organization.id


def test_auth_me_exposes_permissions_by_role(client, db_session):
    user_token = register_and_login(client, "perm-user@example.com", "password123", "Perm User")
    user_me = client.get("/auth/me", headers=auth_headers(user_token))
    assert user_me.status_code == 200
    assert user_me.json()["permissions"] == {
        "manage_organization": False,
        "manage_staff": False,
        "view_metrics": False,
        "manage_inventory": False,
        "manage_timeslots": False,
        "manage_whatsapp": False,
    }

    staff_user = db_session.query(User).filter(User.email == "perm-user@example.com").first()
    staff_user.role = "staff"
    db_session.commit()

    staff_token = client.post(
        "/auth/login",
        data={"username": "perm-user@example.com", "password": "password123"},
    ).json()["access_token"]
    staff_me = client.get("/auth/me", headers=auth_headers(staff_token))
    assert staff_me.status_code == 200
    assert staff_me.json()["permissions"] == {
        "manage_organization": False,
        "manage_staff": False,
        "view_metrics": True,
        "manage_inventory": True,
        "manage_timeslots": True,
        "manage_whatsapp": False,
    }

    staff_user.role = "admin"
    db_session.commit()

    admin_token = client.post(
        "/auth/login",
        data={"username": "perm-user@example.com", "password": "password123"},
    ).json()["access_token"]
    admin_me = client.get("/auth/me", headers=auth_headers(admin_token))
    assert admin_me.status_code == 200
    assert admin_me.json()["permissions"] == {
        "manage_organization": True,
        "manage_staff": True,
        "view_metrics": True,
        "manage_inventory": True,
        "manage_timeslots": True,
        "manage_whatsapp": True,
    }


def test_admin_route_requires_admin_role(client, db_session):
    user_token = register_and_login(client, "normal@example.com", "password123", "Normal User")
    forbidden_response = client.get("/admin/me", headers=auth_headers(user_token))
    assert forbidden_response.status_code == 403
    assert forbidden_response.json()["detail"] == "Acceso exclusivo para gestión de staff"

    admin_user = db_session.query(User).filter(User.email == "normal@example.com").first()
    admin_user.role = "admin"
    db_session.commit()

    admin_token = client.post(
        "/auth/login",
        data={"username": "normal@example.com", "password": "password123"},
    ).json()["access_token"]

    admin_response = client.get("/admin/me", headers=auth_headers(admin_token))
    assert admin_response.status_code == 200
    assert admin_response.json()["role"] == "admin"

    users_response = client.get("/admin/users", headers=auth_headers(admin_token))
    assert users_response.status_code == 200
    assert users_response.json()[0]["role"] in {"admin", "user"}


def test_only_admin_can_create_timeslots(client, db_session):
    seed = seed_timeslot(db_session, capacity=2)
    user_token = register_and_login(client, "timeslot-user@example.com", "password123", "Timeslot User")

    forbidden_response = client.post(
        "/timeslots",
        json={
            "court_id": str(seed.court_id),
            "starts_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
            "ends_at": (datetime.now(timezone.utc) + timedelta(days=2, hours=1)).isoformat(),
            "capacity": 1,
            "price": 15000,
            "is_active": True,
        },
        headers=auth_headers(user_token),
    )
    assert forbidden_response.status_code == 403


def test_admin_bulk_create_timeslots_for_multiple_courts(client, db_session):
    seed = seed_timeslot(db_session, capacity=2)
    second_court = Court(
        venue_id=seed.court.venue_id,
        sport_id=seed.court.sport_id,
        name="Cancha 2",
        indoor=False,
        is_active=True,
        organization_id=seed.organization_id,
    )
    db_session.add(second_court)
    db_session.commit()
    db_session.refresh(second_court)

    register_and_login(client, "bulk-admin@example.com", "password123", "Bulk Admin")
    admin_user = db_session.query(User).filter(User.email == "bulk-admin@example.com").first()
    admin_user.role = "admin"
    db_session.commit()

    admin_token = client.post(
        "/auth/login",
        data={"username": "bulk-admin@example.com", "password": "password123"},
    ).json()["access_token"]

    base_day = datetime.now(timezone.utc).replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=4)
    response = client.post(
        "/admin/timeslots/bulk",
        json={
            "court_ids": [str(seed.court_id), str(second_court.id)],
            "window_starts_at": base_day.isoformat(),
            "window_ends_at": (base_day + timedelta(hours=2)).isoformat(),
            "slot_minutes": 60,
            "capacity": 4,
            "price": 18000,
            "is_active": True,
        },
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["created_count"] == 4
    assert payload["skipped_count"] == 0


def test_booking_list_returns_nested_timeslot_details(client, db_session):
    access_token = register_and_login(client, "booking@example.com", "password123")
    timeslot = seed_timeslot(db_session, capacity=2)

    create_response = client.post(
        "/bookings",
        json={"timeslot_id": str(timeslot.id)},
        headers=auth_headers(access_token),
    )
    assert create_response.status_code == 201

    list_response = client.get("/bookings", headers=auth_headers(access_token))
    assert list_response.status_code == 200

    bookings = list_response.json()
    assert len(bookings) == 1
    booking = bookings[0]

    assert booking["timeslot"]["id"] == str(timeslot.id)
    assert booking["timeslot"]["court"]["name"] == "Cancha 1"
    assert booking["timeslot"]["court"]["sport"]["name"] == "Padel"
    assert booking["timeslot"]["court"]["venue"]["name"] == "Complejo Norte"


def test_booking_rejects_when_timeslot_is_full(client, db_session):
    timeslot = seed_timeslot(db_session, capacity=1)

    first_user_token = register_and_login(client, "first@example.com", "password123", "First User")
    second_user_token = register_and_login(client, "second@example.com", "password123", "Second User")

    first_response = client.post(
        "/bookings",
        json={"timeslot_id": str(timeslot.id)},
        headers=auth_headers(first_user_token),
    )
    assert first_response.status_code == 201

    second_response = client.post(
        "/bookings",
        json={"timeslot_id": str(timeslot.id)},
        headers=auth_headers(second_user_token),
    )
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == "El turno ya está completo"
def test_bulk_create_uses_end_time_as_last_allowed_start(client, db_session):
    seed = seed_timeslot(db_session, capacity=2)

    register_and_login(client, "late-admin@example.com", "password123", "Late Admin")
    admin_user = db_session.query(User).filter(User.email == "late-admin@example.com").first()
    admin_user.role = "admin"
    db_session.commit()

    admin_token = client.post(
        "/auth/login",
        data={"username": "late-admin@example.com", "password": "password123"},
    ).json()["access_token"]

    base_day = datetime.now(timezone.utc).replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=5)
    response = client.post(
        "/admin/timeslots/bulk",
        json={
            "court_ids": [str(seed.court_id)],
            "window_starts_at": base_day.isoformat(),
            "window_ends_at": (base_day + timedelta(hours=14)).isoformat(),
            "slot_minutes": 90,
            "capacity": 4,
            "price": 18000,
            "is_active": True,
        },
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 201
    payload = response.json()
    starts = [datetime.fromisoformat(slot["starts_at"].replace("Z", "+00:00")) for slot in payload["created_slots"]]
    assert payload["created_count"] == 10
    assert starts[-1] == base_day + timedelta(hours=13, minutes=30)


def test_non_admin_cannot_manage_venues_or_courts(client, db_session):
    organization = get_default_organization(db_session)
    sport = Sport(name="Tenis", description="Singles y dobles")
    db_session.add(sport)
    db_session.commit()
    db_session.refresh(sport)

    user_token = register_and_login(client, "inventory-user@example.com", "password123", "Inventory User")

    venue_response = client.post(
        "/venues",
        json={
            "name": "Sede Sur",
            "address": "Calle 123",
            "timezone": "America/Argentina/Buenos_Aires",
            "allowed_sport_id": str(sport.id),
        },
        headers=auth_headers(user_token),
    )
    assert venue_response.status_code == 403

    venue = Venue(
        name="Sede Base",
        address="Base 100",
        timezone="America/Argentina/Buenos_Aires",
        allowed_sport_id=sport.id,
        organization_id=organization.id,
    )
    db_session.add(venue)
    db_session.commit()
    db_session.refresh(venue)

    court_response = client.post(
        "/courts",
        json={
            "venue_id": str(venue.id),
            "sport_id": str(sport.id),
            "name": "Cancha B",
            "indoor": True,
            "is_active": True,
        },
        headers=auth_headers(user_token),
    )
    assert court_response.status_code == 403


def test_staff_can_manage_operational_resources_but_not_org_settings(client, db_session):
    sport = Sport(name="Vóley", description="Operación staff")
    db_session.add(sport)
    db_session.commit()
    db_session.refresh(sport)

    onboard_response = client.post(
        "/organizations/onboard",
        json={
            "organization_name": "Complejo Staff Ops",
            "admin_full_name": "Owner Ops",
            "admin_email": "owner-ops@saas.com",
            "admin_password": "password123",
        },
    )
    assert onboard_response.status_code == 201
    admin_token = onboard_response.json()["access_token"]

    invite_response = client.post(
        "/organizations/current/staff-invitations",
        json={
            "email": "staff-ops@saas.com",
            "full_name": "Staff Ops",
            "role": "staff",
            "expires_in_days": 7,
        },
        headers=auth_headers(admin_token),
    )
    assert invite_response.status_code == 201

    accept_response = client.post(
        "/organizations/staff-invitations/accept",
        json={
            "token": invite_response.json()["invite_token"],
            "full_name": "Staff Ops",
            "password": "password123",
        },
    )
    assert accept_response.status_code == 200
    staff_token = accept_response.json()["access_token"]

    venue_response = client.post(
        "/venues",
        json={
            "name": "Sede Staff",
            "address": "Operativa 123",
            "timezone": "America/Argentina/Buenos_Aires",
            "allowed_sport_id": str(sport.id),
        },
        headers=auth_headers(staff_token),
    )
    assert venue_response.status_code == 201

    metrics_response = client.get("/admin/metrics", headers=auth_headers(staff_token))
    assert metrics_response.status_code == 200

    forbidden_org_response = client.patch(
        "/organizations/current",
        json={"name": "No debería poder"},
        headers=auth_headers(staff_token),
    )
    assert forbidden_org_response.status_code == 403

    forbidden_whatsapp_response = client.patch(
        "/organizations/current/settings",
        json={"whatsapp_provider": "meta_cloud"},
        headers=auth_headers(staff_token),
    )
    assert forbidden_whatsapp_response.status_code == 403


def test_admin_can_create_update_and_delete_venue_and_court(client, db_session):
    sport = Sport(name="Fútbol 5", description="Turnos nocturnos")
    db_session.add(sport)
    db_session.commit()
    db_session.refresh(sport)

    register_and_login(client, "inventory-admin@example.com", "password123", "Inventory Admin")
    admin_user = db_session.query(User).filter(User.email == "inventory-admin@example.com").first()
    admin_user.role = "admin"
    db_session.commit()

    admin_token = client.post(
        "/auth/login",
        data={"username": "inventory-admin@example.com", "password": "password123"},
    ).json()["access_token"]

    create_venue_response = client.post(
        "/venues",
        json={
            "name": "Sede Oeste",
            "address": "Av. del Deporte 500",
            "timezone": "America/Argentina/Buenos_Aires",
            "allowed_sport_id": str(sport.id),
        },
        headers=auth_headers(admin_token),
    )
    assert create_venue_response.status_code == 201
    venue_id = create_venue_response.json()["id"]

    update_venue_response = client.patch(
        f"/venues/{venue_id}",
        json={"name": "Sede Oeste Renovada", "address": "Av. del Deporte 550"},
        headers=auth_headers(admin_token),
    )
    assert update_venue_response.status_code == 200
    assert update_venue_response.json()["name"] == "Sede Oeste Renovada"

    create_court_response = client.post(
        "/courts",
        json={
            "venue_id": venue_id,
            "sport_id": str(sport.id),
            "name": "Cancha Central",
            "indoor": False,
            "is_active": True,
        },
        headers=auth_headers(admin_token),
    )
    assert create_court_response.status_code == 201
    court_id = create_court_response.json()["id"]

    update_court_response = client.patch(
        f"/courts/{court_id}",
        json={"name": "Cancha Central 2", "indoor": True, "is_active": False},
        headers=auth_headers(admin_token),
    )
    assert update_court_response.status_code == 200
    assert update_court_response.json()["name"] == "Cancha Central 2"
    assert update_court_response.json()["is_active"] is False

    delete_court_response = client.delete(f"/courts/{court_id}", headers=auth_headers(admin_token))
    assert delete_court_response.status_code == 204

    delete_venue_response = client.delete(f"/venues/{venue_id}", headers=auth_headers(admin_token))
    assert delete_venue_response.status_code == 204


def test_admin_delete_blocks_for_related_courts_and_timeslots(client, db_session):
    timeslot = seed_timeslot(db_session, capacity=2)

    register_and_login(client, "inventory-admin-block@example.com", "password123", "Inventory Admin Block")
    admin_user = db_session.query(User).filter(User.email == "inventory-admin-block@example.com").first()
    admin_user.role = "admin"
    db_session.commit()

    admin_token = client.post(
        "/auth/login",
        data={"username": "inventory-admin-block@example.com", "password": "password123"},
    ).json()["access_token"]

    delete_court_response = client.delete(
        f"/courts/{timeslot.court_id}",
        headers=auth_headers(admin_token),
    )
    assert delete_court_response.status_code == 409
    assert delete_court_response.json()["detail"] == "No se puede eliminar una cancha con turnos futuros asociados"

    delete_venue_response = client.delete(
        f"/venues/{timeslot.court.venue_id}",
        headers=auth_headers(admin_token),
    )
    assert delete_venue_response.status_code == 409
    assert delete_venue_response.json()["detail"] == "No se puede eliminar una sede con canchas asociadas"


def test_admin_can_delete_court_with_only_expired_timeslots_and_no_bookings(client, db_session):
    timeslot = seed_timeslot(db_session, capacity=2)
    expired_start = datetime.now(timezone.utc) - timedelta(days=2)
    timeslot.starts_at = expired_start
    timeslot.ends_at = expired_start + timedelta(hours=1)
    db_session.commit()

    register_and_login(client, "inventory-admin-expired@example.com", "password123", "Inventory Admin Expired")
    admin_user = db_session.query(User).filter(User.email == "inventory-admin-expired@example.com").first()
    admin_user.role = "admin"
    db_session.commit()

    admin_token = client.post(
        "/auth/login",
        data={"username": "inventory-admin-expired@example.com", "password": "password123"},
    ).json()["access_token"]

    delete_court_response = client.delete(
        f"/courts/{timeslot.court_id}",
        headers=auth_headers(admin_token),
    )
    assert delete_court_response.status_code == 204
    assert db_session.get(Court, timeslot.court_id) is None


def test_admin_delete_blocks_court_with_bookings_even_if_timeslot_is_expired(client, db_session):
    timeslot = seed_timeslot(db_session, capacity=2)
    access_token = register_and_login(client, "inventory-booking@example.com", "password123", "Inventory Booking")

    create_response = client.post(
        "/bookings",
        json={"timeslot_id": str(timeslot.id)},
        headers=auth_headers(access_token),
    )
    assert create_response.status_code == 201

    timeslot.starts_at = datetime.now(timezone.utc) - timedelta(days=1, hours=2)
    timeslot.ends_at = datetime.now(timezone.utc) - timedelta(days=1)
    db_session.commit()

    register_and_login(client, "inventory-admin-booking@example.com", "password123", "Inventory Admin Booking")
    admin_user = db_session.query(User).filter(User.email == "inventory-admin-booking@example.com").first()
    admin_user.role = "admin"
    db_session.commit()

    admin_token = client.post(
        "/auth/login",
        data={"username": "inventory-admin-booking@example.com", "password": "password123"},
    ).json()["access_token"]

    delete_court_response = client.delete(
        f"/courts/{timeslot.court_id}",
        headers=auth_headers(admin_token),
    )
    assert delete_court_response.status_code == 409
    assert delete_court_response.json()["detail"] == "No se puede eliminar una cancha con reservas asociadas"


def test_booking_can_be_cancelled_and_list_reflects_status(client, db_session):
    access_token = register_and_login(client, "cancel@example.com", "password123", "Cancel User")
    timeslot = seed_timeslot(db_session, capacity=2)

    create_response = client.post(
        "/bookings",
        json={"timeslot_id": str(timeslot.id)},
        headers=auth_headers(access_token),
    )
    assert create_response.status_code == 201
    booking_id = create_response.json()["id"]

    cancel_response = client.patch(
        f"/bookings/{booking_id}/cancel",
        headers=auth_headers(access_token),
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"

    list_response = client.get("/bookings", headers=auth_headers(access_token))
    assert list_response.status_code == 200
    assert list_response.json()[0]["status"] == "cancelled"


def test_cancelled_booking_frees_capacity_and_can_be_reconfirmed(client, db_session):
    timeslot = seed_timeslot(db_session, capacity=1)

    first_user_token = register_and_login(client, "cancel-first@example.com", "password123", "Cancel First")
    second_user_token = register_and_login(client, "cancel-second@example.com", "password123", "Cancel Second")

    first_booking = client.post(
        "/bookings",
        json={"timeslot_id": str(timeslot.id)},
        headers=auth_headers(first_user_token),
    )
    assert first_booking.status_code == 201
    booking_id = first_booking.json()["id"]

    cancel_response = client.patch(
        f"/bookings/{booking_id}/cancel",
        headers=auth_headers(first_user_token),
    )
    assert cancel_response.status_code == 200

    second_booking = client.post(
        "/bookings",
        json={"timeslot_id": str(timeslot.id)},
        headers=auth_headers(second_user_token),
    )
    assert second_booking.status_code == 201

    reconfirm_response = client.post(
        "/bookings",
        json={"timeslot_id": str(timeslot.id)},
        headers=auth_headers(first_user_token),
    )
    assert reconfirm_response.status_code == 409
    assert reconfirm_response.json()["detail"] == "El turno ya está completo"


def test_same_user_can_reconfirm_cancelled_booking_when_slot_is_available(client, db_session):
    access_token = register_and_login(client, "reconfirm@example.com", "password123", "Reconfirm User")
    timeslot = seed_timeslot(db_session, capacity=1)

    first_booking = client.post(
        "/bookings",
        json={"timeslot_id": str(timeslot.id)},
        headers=auth_headers(access_token),
    )
    assert first_booking.status_code == 201
    booking_id = first_booking.json()["id"]

    cancel_response = client.patch(
        f"/bookings/{booking_id}/cancel",
        headers=auth_headers(access_token),
    )
    assert cancel_response.status_code == 200

    reconfirm_response = client.post(
        "/bookings",
        json={"timeslot_id": str(timeslot.id)},
        headers=auth_headers(access_token),
    )
    assert reconfirm_response.status_code == 201
    assert reconfirm_response.json()["id"] == booking_id
    assert reconfirm_response.json()["status"] == "confirmed"



def test_timeslot_list_reports_remaining_spots_and_availability(client, db_session):
    timeslot = seed_timeslot(db_session, capacity=3)

    first_user_token = register_and_login(client, "capacity-first@example.com", "password123", "Capacity First")
    second_user_token = register_and_login(client, "capacity-second@example.com", "password123", "Capacity Second")

    first_response = client.post(
        "/bookings",
        json={"timeslot_id": str(timeslot.id)},
        headers=auth_headers(first_user_token),
    )
    assert first_response.status_code == 201

    second_response = client.post(
        "/bookings",
        json={"timeslot_id": str(timeslot.id)},
        headers=auth_headers(second_user_token),
    )
    assert second_response.status_code == 201

    timeslots_response = client.get(
        f"/timeslots?court_id={timeslot.court_id}&limit=100",
    )
    assert timeslots_response.status_code == 200

    payload = timeslots_response.json()[0]
    assert payload["confirmed_bookings"] == 2
    assert payload["remaining_spots"] == 1
    assert payload["availability_status"] == "few_left"


def test_timeslot_list_updates_availability_after_cancellation(client, db_session):
    timeslot = seed_timeslot(db_session, capacity=1)
    access_token = register_and_login(client, "availability-cancel@example.com", "password123", "Availability Cancel")

    booking_response = client.post(
        "/bookings",
        json={"timeslot_id": str(timeslot.id)},
        headers=auth_headers(access_token),
    )
    assert booking_response.status_code == 201

    full_response = client.get(f"/timeslots?court_id={timeslot.court_id}&limit=100")
    assert full_response.status_code == 200
    assert full_response.json()[0]["availability_status"] == "full"
    assert full_response.json()[0]["remaining_spots"] == 0

    cancel_response = client.patch(
        f"/bookings/{booking_response.json()['id']}/cancel",
        headers=auth_headers(access_token),
    )
    assert cancel_response.status_code == 200

    refreshed_response = client.get(f"/timeslots?court_id={timeslot.court_id}&limit=100")
    assert refreshed_response.status_code == 200
    assert refreshed_response.json()[0]["availability_status"] == "few_left"
    assert refreshed_response.json()[0]["remaining_spots"] == 1


def test_booking_rejects_inactive_court_and_expired_timeslot(client, db_session):
    access_token = register_and_login(client, "domain-safety@example.com", "password123", "Domain Safety")

    timeslot = seed_timeslot(db_session, capacity=2)
    timeslot.court.is_active = False
    db_session.commit()

    inactive_response = client.post(
        "/bookings",
        json={"timeslot_id": str(timeslot.id)},
        headers=auth_headers(access_token),
    )
    assert inactive_response.status_code == 409
    assert inactive_response.json()["detail"] == "La cancha está inactiva"

    timeslot.court.is_active = True
    timeslot.starts_at = datetime.now(timezone.utc) - timedelta(minutes=30)
    timeslot.ends_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    db_session.commit()

    expired_response = client.post(
        "/bookings",
        json={"timeslot_id": str(timeslot.id)},
        headers=auth_headers(access_token),
    )
    assert expired_response.status_code == 409
    assert expired_response.json()["detail"] == "El turno ya no admite reservas"


def test_timeslot_create_and_bulk_block_inactive_courts(client, db_session):
    seed = seed_timeslot(db_session, capacity=2)
    seed.court.is_active = False
    db_session.commit()

    register_and_login(client, "inactive-court-admin@example.com", "password123", "Inactive Court Admin")
    admin_user = db_session.query(User).filter(User.email == "inactive-court-admin@example.com").first()
    admin_user.role = "admin"
    db_session.commit()

    admin_token = client.post(
        "/auth/login",
        data={"username": "inactive-court-admin@example.com", "password": "password123"},
    ).json()["access_token"]

    single_response = client.post(
        "/timeslots",
        json={
            "court_id": str(seed.court_id),
            "starts_at": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
            "ends_at": (datetime.now(timezone.utc) + timedelta(days=3, hours=1)).isoformat(),
            "capacity": 2,
            "price": 15000,
            "is_active": True,
        },
        headers=auth_headers(admin_token),
    )
    assert single_response.status_code == 409
    assert single_response.json()["detail"] == "No se pueden crear o activar turnos sobre una cancha inactiva"

    base_day = datetime.now(timezone.utc).replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=4)
    bulk_response = client.post(
        "/admin/timeslots/bulk",
        json={
            "court_ids": [str(seed.court_id)],
            "window_starts_at": base_day.isoformat(),
            "window_ends_at": (base_day + timedelta(hours=2)).isoformat(),
            "slot_minutes": 60,
            "capacity": 4,
            "price": 18000,
            "is_active": True,
        },
        headers=auth_headers(admin_token),
    )
    assert bulk_response.status_code == 409
    assert bulk_response.json()["detail"] == "No se pueden generar turnos sobre canchas inactivas: Cancha 1"


def test_timeslot_update_blocks_capacity_below_confirmed_bookings(client, db_session):
    timeslot = seed_timeslot(db_session, capacity=3)

    first_user_token = register_and_login(client, "capacity-lock-1@example.com", "password123", "Capacity Lock 1")
    second_user_token = register_and_login(client, "capacity-lock-2@example.com", "password123", "Capacity Lock 2")

    first_response = client.post(
        "/bookings",
        json={"timeslot_id": str(timeslot.id)},
        headers=auth_headers(first_user_token),
    )
    assert first_response.status_code == 201

    second_response = client.post(
        "/bookings",
        json={"timeslot_id": str(timeslot.id)},
        headers=auth_headers(second_user_token),
    )
    assert second_response.status_code == 201

    register_and_login(client, "capacity-admin@example.com", "password123", "Capacity Admin")
    admin_user = db_session.query(User).filter(User.email == "capacity-admin@example.com").first()
    admin_user.role = "admin"
    db_session.commit()

    admin_token = client.post(
        "/auth/login",
        data={"username": "capacity-admin@example.com", "password": "password123"},
    ).json()["access_token"]

    update_response = client.patch(
        f"/timeslots/{timeslot.id}",
        json={"capacity": 1},
        headers=auth_headers(admin_token),
    )
    assert update_response.status_code == 409
    assert update_response.json()["detail"] == "La capacidad no puede quedar por debajo de las reservas confirmadas"


def test_timeslot_list_marks_started_slot_as_expired(client, db_session):
    timeslot = seed_timeslot(db_session, capacity=2)
    timeslot.starts_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    timeslot.ends_at = datetime.now(timezone.utc) + timedelta(minutes=50)
    db_session.commit()

    timeslots_response = client.get(f"/timeslots?court_id={timeslot.court_id}&limit=100")
    assert timeslots_response.status_code == 200
    assert timeslots_response.json()[0]["availability_status"] == "expired"



def test_booking_policies_endpoint_exposes_current_rules(client):
    response = client.get("/bookings/policies")
    assert response.status_code == 200
    payload = response.json()
    assert payload["min_booking_lead_minutes"] == 30
    assert payload["cancellation_min_lead_minutes"] == 120


def test_booking_rejects_when_minimum_lead_time_is_not_met(client, db_session):
    access_token = register_and_login(client, "lead-policy@example.com", "password123", "Lead Policy")
    timeslot = seed_timeslot(db_session, capacity=2)
    timeslot.starts_at = datetime.now(timezone.utc) + timedelta(minutes=20)
    timeslot.ends_at = timeslot.starts_at + timedelta(hours=1)
    db_session.commit()

    response = client.post(
        "/bookings",
        json={"timeslot_id": str(timeslot.id)},
        headers=auth_headers(access_token),
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Las reservas de Padel deben hacerse con al menos 30 minutos de anticipación."



def test_timeslot_list_marks_short_notice_slot_as_booking_closed(client, db_session):
    timeslot = seed_timeslot(db_session, capacity=2)
    timeslot.starts_at = datetime.now(timezone.utc) + timedelta(minutes=20)
    timeslot.ends_at = timeslot.starts_at + timedelta(hours=1)
    db_session.commit()

    response = client.get(f"/timeslots?court_id={timeslot.court_id}&limit=100")
    assert response.status_code == 200
    assert response.json()[0]["availability_status"] == "booking_closed"



def test_booking_cancel_rejects_after_cancellation_window(client, db_session):
    access_token = register_and_login(client, "cancel-policy@example.com", "password123", "Cancel Policy")
    timeslot = seed_timeslot(db_session, capacity=2)
    timeslot.starts_at = datetime.now(timezone.utc) + timedelta(minutes=90)
    timeslot.ends_at = timeslot.starts_at + timedelta(hours=1)
    db_session.commit()

    create_response = client.post(
        "/bookings",
        json={"timeslot_id": str(timeslot.id)},
        headers=auth_headers(access_token),
    )
    assert create_response.status_code == 201

    cancel_response = client.patch(
        f"/bookings/{create_response.json()['id']}/cancel",
        headers=auth_headers(access_token),
    )
    assert cancel_response.status_code == 409
    assert cancel_response.json()["detail"] == "Las cancelaciones de Padel se permiten hasta 120 minutos antes del inicio del turno."



def test_booking_list_exposes_cancellation_policy_state(client, db_session):
    access_token = register_and_login(client, "cancel-state@example.com", "password123", "Cancel State")
    timeslot = seed_timeslot(db_session, capacity=2)
    timeslot.starts_at = datetime.now(timezone.utc) + timedelta(minutes=90)
    timeslot.ends_at = timeslot.starts_at + timedelta(hours=1)
    db_session.commit()

    create_response = client.post(
        "/bookings",
        json={"timeslot_id": str(timeslot.id)},
        headers=auth_headers(access_token),
    )
    assert create_response.status_code == 201

    list_response = client.get("/bookings", headers=auth_headers(access_token))
    assert list_response.status_code == 200
    booking = list_response.json()[0]
    assert booking["can_cancel"] is False
    assert booking["cancellation_policy_message"] == "Las cancelaciones de Padel se permiten hasta 120 minutos antes del inicio del turno."


def test_admin_can_update_sport_policy_windows(client, db_session):
    sport = Sport(name="Tenis", description="Singles y dobles")
    db_session.add(sport)
    db_session.commit()
    db_session.refresh(sport)

    register_and_login(client, "sport-policy-admin@example.com", "password123", "Sport Policy Admin")
    admin_user = db_session.query(User).filter(User.email == "sport-policy-admin@example.com").first()
    admin_user.role = "admin"
    db_session.commit()

    admin_token = client.post(
        "/auth/login",
        data={"username": "sport-policy-admin@example.com", "password": "password123"},
    ).json()["access_token"]

    update_response = client.patch(
        f"/sports/{sport.id}",
        json={
            "booking_min_lead_minutes": 90,
            "cancellation_min_lead_minutes": 180,
            "description": "Necesita más organización previa",
        },
        headers=auth_headers(admin_token),
    )

    assert update_response.status_code == 200
    assert update_response.json()["booking_min_lead_minutes"] == 90
    assert update_response.json()["cancellation_min_lead_minutes"] == 180

    policy_response = client.get(f"/bookings/policies?sport_id={sport.id}")
    assert policy_response.status_code == 200
    assert policy_response.json()["uses_default_policy"] is False
    assert policy_response.json()["booking_message"] == "Las reservas de Tenis deben hacerse con al menos 90 minutos de anticipación."


def test_sport_specific_policy_marks_slot_as_booking_closed(client, db_session):
    timeslot = seed_timeslot(db_session, capacity=2)
    timeslot.court.sport.booking_min_lead_minutes = 90
    timeslot.starts_at = datetime.now(timezone.utc) + timedelta(minutes=60)
    timeslot.ends_at = timeslot.starts_at + timedelta(hours=1)
    db_session.commit()

    response = client.get(f"/timeslots?court_id={timeslot.court_id}&limit=100")
    assert response.status_code == 200
    payload = response.json()[0]
    assert payload["availability_status"] == "booking_closed"
    assert payload["policy_summary"] == "Esta configuración específica aplica al deporte Padel."

def test_register_stores_whatsapp_preferences(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "whatsapp-user@example.com",
            "password": "password123",
            "full_name": "WhatsApp User",
            "whatsapp_number": "+54 9 11 2233 4455",
            "whatsapp_opt_in": True,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["whatsapp_number"] == "5491122334455"
    assert payload["whatsapp_opt_in"] is True


def test_user_can_update_own_whatsapp_preferences(client):
    access_token = register_and_login(client, "update-whatsapp@example.com", "password123", "Update WhatsApp")

    response = client.patch(
        "/auth/me",
        json={
            "whatsapp_number": "+54 9 11 9988 7766",
            "whatsapp_opt_in": True,
        },
        headers=auth_headers(access_token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["whatsapp_number"] == "5491199887766"
    assert payload["whatsapp_opt_in"] is True


def test_booking_and_cancel_trigger_whatsapp_notifications_when_user_opted_in(client, db_session, monkeypatch):
    access_token = register_and_login(client, "notify-booking@example.com", "password123", "Notify Booking")
    user = db_session.query(User).filter(User.email == "notify-booking@example.com").first()
    user.whatsapp_number = "5491112345678"
    user.whatsapp_opt_in = True
    db_session.commit()

    timeslot = seed_timeslot(db_session, capacity=2)

    sent_events: list[str] = []

    monkeypatch.setattr(
        "app.api.routes.bookings.send_booking_confirmed_notification",
        lambda booking: sent_events.append(f"confirmed:{booking.id}") or True,
    )
    monkeypatch.setattr(
        "app.api.routes.bookings.send_booking_cancelled_notification",
        lambda booking: sent_events.append(f"cancelled:{booking.id}") or True,
    )

    create_response = client.post(
        "/bookings",
        json={"timeslot_id": str(timeslot.id)},
        headers=auth_headers(access_token),
    )
    assert create_response.status_code == 201
    booking_id = create_response.json()["id"]
    assert sent_events == [f"confirmed:{booking_id}"]

    cancel_response = client.patch(
        f"/bookings/{booking_id}/cancel",
        headers=auth_headers(access_token),
    )
    assert cancel_response.status_code == 200
    assert sent_events == [f"confirmed:{booking_id}", f"cancelled:{booking_id}"]


def test_admin_can_check_notification_status(client, db_session):
    register_and_login(client, "notification-admin@example.com", "password123", "Notification Admin")
    admin_user = db_session.query(User).filter(User.email == "notification-admin@example.com").first()
    admin_user.role = "admin"
    db_session.commit()

    admin_token = client.post(
        "/auth/login",
        data={"username": "notification-admin@example.com", "password": "password123"},
    ).json()["access_token"]

    response = client.get("/admin/notification-status", headers=auth_headers(admin_token))
    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] in {"disabled", "meta_cloud"}
    assert "configured" in payload
    assert "ready_for_live_send" in payload
    assert isinstance(payload["checks"], list)
    assert any(check["key"] == "booking_confirmed_template" for check in payload["checks"])
    assert isinstance(payload["missing_items"], list)


def test_admin_metrics_aggregates_operational_summary(client, db_session):
    timeslot = seed_timeslot(db_session, capacity=3)

    register_and_login(client, "metrics-admin@example.com", "password123", "Metrics Admin")
    admin_user = db_session.query(User).filter(User.email == "metrics-admin@example.com").first()
    admin_user.role = "admin"
    db_session.commit()

    admin_token = client.post(
        "/auth/login",
        data={"username": "metrics-admin@example.com", "password": "password123"},
    ).json()["access_token"]

    first_user_token = register_and_login(client, "metrics-user-1@example.com", "password123", "Metrics User 1")
    second_user_token = register_and_login(client, "metrics-user-2@example.com", "password123", "Metrics User 2")

    first_booking = client.post(
        "/bookings",
        json={"timeslot_id": str(timeslot.id)},
        headers=auth_headers(first_user_token),
    )
    assert first_booking.status_code == 201

    second_booking = client.post(
        "/bookings",
        json={"timeslot_id": str(timeslot.id)},
        headers=auth_headers(second_user_token),
    )
    assert second_booking.status_code == 201

    cancel_second = client.patch(
        f"/bookings/{second_booking.json()['id']}/cancel",
        headers=auth_headers(second_user_token),
    )
    assert cancel_second.status_code == 200

    response = client.get(
        "/admin/metrics",
        params={
            "date_from": (timeslot.starts_at - timedelta(hours=1)).isoformat(),
            "date_to": (timeslot.starts_at + timedelta(hours=1)).isoformat(),
        },
        headers=auth_headers(admin_token),
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["summary"]["total_timeslots"] == 1
    assert payload["summary"]["confirmed_bookings"] == 1
    assert payload["summary"]["cancelled_bookings"] == 1
    assert payload["summary"]["spots_total"] == 3
    assert payload["summary"]["spots_filled"] == 1
    assert payload["summary"]["estimated_revenue"] == 12000.0
    assert payload["by_sport"][0]["name"] == "Padel"
    assert payload["by_venue"][0]["name"] == "Complejo Norte"


def test_public_venue_listing_uses_default_organization_scope(client, db_session):
    register_and_login(client, "tenant-owner@example.com", "password123", "Tenant Owner")

    default_org = get_default_organization(db_session)

    sport = Sport(name="Hockey", description="Canchas y entrenamiento")
    db_session.add(sport)
    db_session.flush()

    other_org = Organization(name="Complejo Sur", slug="complejo-sur", is_active=True)
    db_session.add(other_org)
    db_session.flush()

    default_venue = Venue(
        name="Sede Demo",
        address="Norte 123",
        timezone="America/Argentina/Buenos_Aires",
        allowed_sport_id=sport.id,
        organization_id=default_org.id,
    )
    other_venue = Venue(
        name="Sede Sur",
        address="Sur 456",
        timezone="America/Argentina/Buenos_Aires",
        allowed_sport_id=sport.id,
        organization_id=other_org.id,
    )
    db_session.add(default_venue)
    db_session.add(other_venue)
    db_session.commit()

    response = client.get("/venues?limit=100")
    assert response.status_code == 200
    names = [venue["name"] for venue in response.json()]
    assert "Sede Demo" in names
    assert "Sede Sur" not in names


def test_current_organization_can_disable_sports_from_global_catalog(client, db_session):
    db_session.add_all(
        [
            Sport(name="Tenis", description="Catálogo global"),
            Sport(name="Padel", description="Catálogo global"),
        ]
    )
    db_session.commit()

    onboard_response = onboard_organization(
        client,
        organization_name="Complejo Deportes",
        organization_slug="complejo-deportes",
        admin_email="deportes-admin@saas.com",
    )
    admin_token = onboard_response["access_token"]

    catalog_response = client.get("/sports/catalog", headers=auth_headers(admin_token))
    assert catalog_response.status_code == 200
    catalog = catalog_response.json()
    assert len(catalog) >= 1

    enabled_response = client.get("/sports", headers=auth_headers(admin_token))
    assert enabled_response.status_code == 200
    assert len(enabled_response.json()) == len(catalog)

    target_sport_id = catalog[0]["id"]
    remaining_ids = [sport["id"] for sport in catalog[1:]]

    update_response = client.patch(
        "/organizations/current/sports",
        json={"enabled_sport_ids": remaining_ids},
        headers=auth_headers(admin_token),
    )
    assert update_response.status_code == 200

    current_sports_response = client.get("/organizations/current/sports", headers=auth_headers(admin_token))
    assert current_sports_response.status_code == 200
    current_sports = current_sports_response.json()
    toggled_sport = next(item for item in current_sports if item["sport"]["id"] == target_sport_id)
    assert toggled_sport["is_enabled"] is False

    visible_sports_response = client.get("/sports", headers=auth_headers(admin_token))
    assert visible_sports_response.status_code == 200
    visible_ids = {sport["id"] for sport in visible_sports_response.json()}
    assert target_sport_id not in visible_ids


def test_disabled_sport_is_blocked_for_operational_setup(client, db_session):
    db_session.add_all(
        [
            Sport(name="Básquet", description="Catálogo global"),
            Sport(name="Vóley", description="Catálogo global"),
        ]
    )
    db_session.commit()

    sport_a = onboard_organization(
        client,
        organization_name="Complejo Setup",
        organization_slug="complejo-setup",
        admin_email="setup-admin@saas.com",
    )
    admin_token = sport_a["access_token"]

    catalog_response = client.get("/sports/catalog", headers=auth_headers(admin_token))
    assert catalog_response.status_code == 200
    catalog = catalog_response.json()
    assert len(catalog) >= 2

    disabled_sport = catalog[0]
    enabled_sport = catalog[1]

    disable_response = client.patch(
        "/organizations/current/sports",
        json={"enabled_sport_ids": [enabled_sport["id"]]},
        headers=auth_headers(admin_token),
    )
    assert disable_response.status_code == 200

    venue_response = client.post(
        "/venues",
        json={
            "name": "Sede Setup",
            "address": "Calle Setup 100",
            "timezone": "America/Argentina/Buenos_Aires",
            "allowed_sport_id": disabled_sport["id"],
        },
        headers=auth_headers(admin_token),
    )
    assert venue_response.status_code == 400
    assert venue_response.json()["detail"] == "El deporte no está habilitado para este complejo"

    enabled_venue_response = client.post(
        "/venues",
        json={
            "name": "Sede Setup OK",
            "address": "Calle Setup 200",
            "timezone": "America/Argentina/Buenos_Aires",
            "allowed_sport_id": enabled_sport["id"],
        },
        headers=auth_headers(admin_token),
    )
    assert enabled_venue_response.status_code == 201

    court_response = client.post(
        "/courts",
        json={
            "venue_id": enabled_venue_response.json()["id"],
            "sport_id": disabled_sport["id"],
            "name": "Cancha no válida",
            "indoor": True,
            "is_active": True,
        },
        headers=auth_headers(admin_token),
    )
    assert court_response.status_code == 400
    assert court_response.json()["detail"] == "El deporte no está habilitado para este complejo"


def test_admin_cannot_manage_other_tenant_operational_resources(client, db_session):
    sport = Sport(name="Hockey", description="Aislamiento admin")
    db_session.add(sport)
    db_session.commit()
    db_session.refresh(sport)

    tenant_a = onboard_organization(
        client,
        organization_name="Complejo Admin A",
        organization_slug="complejo-admin-a",
        admin_email="admin-a@saas.com",
    )
    tenant_b = onboard_organization(
        client,
        organization_name="Complejo Admin B",
        organization_slug="complejo-admin-b",
        admin_email="admin-b@saas.com",
    )

    admin_a_token = tenant_a["access_token"]
    admin_b_token = tenant_b["access_token"]

    venue_response = client.post(
        "/venues",
        json={
            "name": "Sede B",
            "address": "Calle Tenant B 100",
            "timezone": "America/Argentina/Buenos_Aires",
            "allowed_sport_id": str(sport.id),
        },
        headers=auth_headers(admin_b_token),
    )
    assert venue_response.status_code == 201
    venue_id = venue_response.json()["id"]

    court_response = client.post(
        "/courts",
        json={
            "venue_id": venue_id,
            "sport_id": str(sport.id),
            "name": "Cancha B1",
            "indoor": True,
            "is_active": True,
        },
        headers=auth_headers(admin_b_token),
    )
    assert court_response.status_code == 201
    court_id = court_response.json()["id"]

    timeslot_response = client.post(
        "/timeslots",
        json={
            "court_id": court_id,
            "starts_at": (datetime.now(timezone.utc) + timedelta(days=4)).isoformat(),
            "ends_at": (datetime.now(timezone.utc) + timedelta(days=4, hours=1)).isoformat(),
            "capacity": 4,
            "price": 18000,
            "is_active": True,
        },
        headers=auth_headers(admin_b_token),
    )
    assert timeslot_response.status_code == 201
    timeslot_id = timeslot_response.json()["id"]

    visible_venues_response = client.get("/venues", headers=auth_headers(admin_a_token))
    assert visible_venues_response.status_code == 200
    assert visible_venues_response.json() == []

    update_venue_response = client.patch(
        f"/venues/{venue_id}",
        json={"name": "No debería verse"},
        headers=auth_headers(admin_a_token),
    )
    assert update_venue_response.status_code == 404

    update_court_response = client.patch(
        f"/courts/{court_id}",
        json={"name": "No debería verse"},
        headers=auth_headers(admin_a_token),
    )
    assert update_court_response.status_code == 404

    update_timeslot_response = client.patch(
        f"/timeslots/{timeslot_id}",
        json={"capacity": 6},
        headers=auth_headers(admin_a_token),
    )
    assert update_timeslot_response.status_code == 404


def test_staff_cannot_operate_other_tenant_courts(client, db_session):
    sport = Sport(name="Squash", description="Aislamiento staff")
    db_session.add(sport)
    db_session.commit()
    db_session.refresh(sport)

    owner_ops = onboard_organization(
        client,
        organization_name="Complejo Staff A",
        organization_slug="complejo-staff-a",
        admin_email="owner-staff-a@saas.com",
    )
    owner_other = onboard_organization(
        client,
        organization_name="Complejo Staff B",
        organization_slug="complejo-staff-b",
        admin_email="owner-staff-b@saas.com",
    )

    invite_response = client.post(
        "/organizations/current/staff-invitations",
        json={
            "email": "staff-a@saas.com",
            "full_name": "Staff A",
            "role": "staff",
            "expires_in_days": 7,
        },
        headers=auth_headers(owner_ops["access_token"]),
    )
    assert invite_response.status_code == 201

    accept_response = client.post(
        "/organizations/staff-invitations/accept",
        json={
            "token": invite_response.json()["invite_token"],
            "full_name": "Staff A",
            "password": "password123",
        },
    )
    assert accept_response.status_code == 200
    staff_token = accept_response.json()["access_token"]

    venue_response = client.post(
        "/venues",
        json={
            "name": "Sede B",
            "address": "Calle Tenant B 200",
            "timezone": "America/Argentina/Buenos_Aires",
            "allowed_sport_id": str(sport.id),
        },
        headers=auth_headers(owner_other["access_token"]),
    )
    assert venue_response.status_code == 201

    court_response = client.post(
        "/courts",
        json={
            "venue_id": venue_response.json()["id"],
            "sport_id": str(sport.id),
            "name": "Cancha B2",
            "indoor": False,
            "is_active": True,
        },
        headers=auth_headers(owner_other["access_token"]),
    )
    assert court_response.status_code == 201

    create_timeslot_response = client.post(
        "/timeslots",
        json={
            "court_id": court_response.json()["id"],
            "starts_at": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
            "ends_at": (datetime.now(timezone.utc) + timedelta(days=5, hours=1)).isoformat(),
            "capacity": 4,
            "price": 22000,
            "is_active": True,
        },
        headers=auth_headers(staff_token),
    )
    assert create_timeslot_response.status_code == 400
    assert create_timeslot_response.json()["detail"] == "Cancha no encontrada"

    bulk_response = client.post(
        "/admin/timeslots/bulk",
        json={
            "court_ids": [court_response.json()["id"]],
            "window_starts_at": (datetime.now(timezone.utc) + timedelta(days=6)).isoformat(),
            "window_ends_at": (datetime.now(timezone.utc) + timedelta(days=6, hours=2)).isoformat(),
            "slot_minutes": 60,
            "capacity": 4,
            "price": 18000,
            "is_active": True,
        },
        headers=auth_headers(staff_token),
    )
    assert bulk_response.status_code == 400
    assert "court_id not found" in bulk_response.json()["detail"]


def test_user_cannot_book_timeslot_from_other_tenant(client, db_session):
    sport = Sport(name="Básquet", description="Aislamiento booking")
    db_session.add(sport)
    db_session.commit()
    db_session.refresh(sport)

    tenant_b = onboard_organization(
        client,
        organization_name="Complejo Booking B",
        organization_slug="complejo-booking-b",
        admin_email="owner-booking-b@saas.com",
    )

    venue_response = client.post(
        "/venues",
        json={
            "name": "Sede Booking B",
            "address": "Calle Tenant B 300",
            "timezone": "America/Argentina/Buenos_Aires",
            "allowed_sport_id": str(sport.id),
        },
        headers=auth_headers(tenant_b["access_token"]),
    )
    assert venue_response.status_code == 201

    court_response = client.post(
        "/courts",
        json={
            "venue_id": venue_response.json()["id"],
            "sport_id": str(sport.id),
            "name": "Cancha Booking B",
            "indoor": True,
            "is_active": True,
        },
        headers=auth_headers(tenant_b["access_token"]),
    )
    assert court_response.status_code == 201

    timeslot_response = client.post(
        "/timeslots",
        json={
            "court_id": court_response.json()["id"],
            "starts_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            "ends_at": (datetime.now(timezone.utc) + timedelta(days=7, hours=1)).isoformat(),
            "capacity": 4,
            "price": 24000,
            "is_active": True,
        },
        headers=auth_headers(tenant_b["access_token"]),
    )
    assert timeslot_response.status_code == 201

    default_user_token = register_and_login(
        client,
        "tenant-a-user@example.com",
        "password123",
        "Tenant A User",
    )

    booking_response = client.post(
        "/bookings",
        json={"timeslot_id": timeslot_response.json()["id"]},
        headers=auth_headers(default_user_token),
    )
    assert booking_response.status_code == 404
    assert booking_response.json()["detail"] == "Turno no disponible"


def test_core_records_created_through_flows_store_organization_id(client, db_session):
    organization = get_default_organization(db_session)

    sport = Sport(name="Básquet", description="Media cancha y partidos")
    db_session.add(sport)
    db_session.commit()
    db_session.refresh(sport)

    register_and_login(client, "tenant-admin@example.com", "password123", "Tenant Admin")
    admin_user = db_session.query(User).filter(User.email == "tenant-admin@example.com").first()
    admin_user.role = "admin"
    db_session.commit()

    admin_token = client.post(
        "/auth/login",
        data={"username": "tenant-admin@example.com", "password": "password123"},
    ).json()["access_token"]

    venue_response = client.post(
        "/venues",
        json={
            "name": "Sede Tenant",
            "address": "Tenant 123",
            "timezone": "America/Argentina/Buenos_Aires",
            "allowed_sport_id": str(sport.id),
        },
        headers=auth_headers(admin_token),
    )
    assert venue_response.status_code == 201

    court_response = client.post(
        "/courts",
        json={
            "venue_id": venue_response.json()["id"],
            "sport_id": str(sport.id),
            "name": "Cancha Tenant",
            "indoor": True,
            "is_active": True,
        },
        headers=auth_headers(admin_token),
    )
    assert court_response.status_code == 201

    starts_at = datetime.now(timezone.utc) + timedelta(days=2)
    timeslot_response = client.post(
        "/timeslots",
        json={
            "court_id": court_response.json()["id"],
            "starts_at": starts_at.isoformat(),
            "ends_at": (starts_at + timedelta(hours=1)).isoformat(),
            "capacity": 1,
            "price": 9000,
            "is_active": True,
        },
        headers=auth_headers(admin_token),
    )
    assert timeslot_response.status_code == 201

    user_token = register_and_login(client, "tenant-player@example.com", "password123", "Tenant Player")
    booking_response = client.post(
        "/bookings",
        json={"timeslot_id": timeslot_response.json()["id"]},
        headers=auth_headers(user_token),
    )
    assert booking_response.status_code == 201

    venue = db_session.get(Venue, venue_response.json()["id"])
    court = db_session.get(Court, court_response.json()["id"])
    timeslot = db_session.get(TimeSlot, timeslot_response.json()["id"])
    booking = db_session.get(Booking, booking_response.json()["id"])
    user = db_session.query(User).filter(User.email == "tenant-player@example.com").first()

    assert venue.organization_id == organization.id
    assert court.organization_id == organization.id
    assert timeslot.organization_id == organization.id
    assert booking.organization_id == organization.id
    assert user.organization_id == organization.id


def test_admin_tenant_integrity_reports_nulls_and_mismatches(client, db_session):
    default_org = get_default_organization(db_session)
    other_org = Organization(name="Complejo Este", slug="complejo-este", is_active=True)
    db_session.add(other_org)
    db_session.commit()
    db_session.refresh(other_org)

    register_and_login(client, "integrity-admin@example.com", "password123", "Integrity Admin")
    admin_user = db_session.query(User).filter(User.email == "integrity-admin@example.com").first()
    admin_user.role = "admin"
    db_session.commit()

    sport = Sport(name="Handball", description="Pruebas multi-tenant")
    db_session.add(sport)
    db_session.flush()

    mismatched_venue = Venue(
        name="Sede Este",
        address="Mismatch 2",
        timezone="America/Argentina/Buenos_Aires",
        allowed_sport_id=sport.id,
        organization_id=other_org.id,
    )
    db_session.add(mismatched_venue)
    db_session.flush()

    mismatched_court = Court(
        name="Cancha Mismatch",
        venue_id=mismatched_venue.id,
        sport_id=sport.id,
        indoor=True,
        is_active=True,
        organization_id=default_org.id,
    )
    db_session.add(mismatched_court)
    db_session.flush()

    mismatched_timeslot = TimeSlot(
        court_id=mismatched_court.id,
        starts_at=datetime.now(timezone.utc) + timedelta(days=3),
        ends_at=datetime.now(timezone.utc) + timedelta(days=3, hours=1),
        capacity=2,
        price=10000,
        is_active=True,
        organization_id=other_org.id,
    )
    db_session.add(mismatched_timeslot)
    db_session.flush()

    mismatched_booking_user = User(
        email="mismatch-user@example.com",
        full_name="Mismatch User",
        hashed_password=get_password_hash("password123"),
        role="user",
        organization_id=other_org.id,
    )
    db_session.add(mismatched_booking_user)
    db_session.flush()

    mismatched_booking = Booking(
        user_id=mismatched_booking_user.id,
        timeslot_id=mismatched_timeslot.id,
        status="confirmed",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        organization_id=default_org.id,
    )
    db_session.add(mismatched_booking)
    db_session.commit()

    admin_token = client.post(
        "/auth/login",
        data={"username": "integrity-admin@example.com", "password": "password123"},
    ).json()["access_token"]

    response = client.get("/admin/tenant-integrity", headers=auth_headers(admin_token))
    assert response.status_code == 200

    payload = response.json()
    assert payload["counts"]["organizations"] == 2
    assert payload["counts"]["users_without_organization"] == 0
    assert payload["counts"]["venues_without_organization"] == 0
    assert payload["counts"]["courts_without_organization"] == 0
    assert payload["counts"]["timeslots_without_organization"] == 0
    assert payload["counts"]["bookings_without_organization"] == 0
    assert payload["issues"]["court_venue_mismatches"] == 1
    assert payload["issues"]["timeslot_court_mismatches"] == 1
    assert payload["issues"]["booking_user_mismatches"] == 1
    assert payload["issues"]["booking_timeslot_mismatches"] == 1
    assert payload["ready_for_not_null"] is False


def test_admin_tenant_integrity_reports_ready_when_dataset_is_consistent(client, db_session):
    seed = seed_timeslot(db_session, capacity=2)

    register_and_login(client, "ready-admin@example.com", "password123", "Ready Admin")
    admin_user = db_session.query(User).filter(User.email == "ready-admin@example.com").first()
    admin_user.role = "admin"
    db_session.commit()

    admin_token = client.post(
        "/auth/login",
        data={"username": "ready-admin@example.com", "password": "password123"},
    ).json()["access_token"]

    user_token = register_and_login(client, "ready-user@example.com", "password123", "Ready User")
    booking_response = client.post(
        "/bookings",
        json={"timeslot_id": str(seed.id)},
        headers=auth_headers(user_token),
    )
    assert booking_response.status_code == 201

    response = client.get("/admin/tenant-integrity", headers=auth_headers(admin_token))
    assert response.status_code == 200

    payload = response.json()
    assert payload["counts"]["users_without_organization"] == 0
    assert payload["counts"]["venues_without_organization"] == 0
    assert payload["counts"]["courts_without_organization"] == 0
    assert payload["counts"]["timeslots_without_organization"] == 0
    assert payload["counts"]["bookings_without_organization"] == 0
    assert payload["issues"]["court_venue_mismatches"] == 0
    assert payload["issues"]["timeslot_court_mismatches"] == 0
    assert payload["issues"]["booking_user_mismatches"] == 0
    assert payload["issues"]["booking_timeslot_mismatches"] == 0
    assert payload["ready_for_not_null"] is True


def test_public_onboarding_creates_organization_and_admin_user(client, db_session):
    response = client.post(
        "/organizations/onboard",
        json={
            "organization_name": "Complejo SaaS Norte",
            "organization_slug": "complejo-saas-norte",
            "admin_full_name": "Owner Admin",
            "admin_email": "owner@saas.com",
            "admin_password": "password123",
            "whatsapp_number": "+54 9 11 7788 9900",
            "whatsapp_opt_in": True,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["organization"]["name"] == "Complejo SaaS Norte"
    assert payload["organization"]["slug"] == "complejo-saas-norte"
    assert payload["access_token"]
    assert payload["refresh_token"]

    organization = db_session.query(Organization).filter(Organization.slug == "complejo-saas-norte").first()
    admin_user = db_session.query(User).filter(User.email == "owner@saas.com").first()

    assert organization is not None
    assert admin_user is not None
    assert admin_user.role == "admin"
    assert admin_user.organization_id == organization.id
    assert admin_user.whatsapp_opt_in is True
    membership = (
        db_session.query(OrganizationMembership)
        .filter(
            OrganizationMembership.user_id == admin_user.id,
            OrganizationMembership.organization_id == organization.id,
        )
        .first()
    )
    assert membership is not None
    assert membership.role == "admin"
    assert membership.is_default is True


def test_onboarding_existing_account_adds_admin_membership_without_losing_previous_one(client, db_session):
    base_token = register_and_login(client, "multi-owner@saas.com", "password123", "Multi Owner")
    base_me = client.get("/auth/me", headers=auth_headers(base_token))
    assert base_me.status_code == 200
    base_org_id = base_me.json()["organization_id"]

    onboard_response = client.post(
        "/organizations/onboard",
        json={
            "organization_name": "Complejo Segundo",
            "organization_slug": "complejo-segundo",
            "admin_full_name": "Multi Owner",
            "admin_email": "multi-owner@saas.com",
            "admin_password": "password123",
        },
    )

    assert onboard_response.status_code == 201
    new_organization_id = onboard_response.json()["organization"]["id"]
    assert new_organization_id != base_org_id

    user = db_session.query(User).filter(User.email == "multi-owner@saas.com").first()
    memberships = (
        db_session.query(OrganizationMembership)
        .filter(OrganizationMembership.user_id == user.id)
        .order_by(OrganizationMembership.created_at.asc())
        .all()
    )
    assert len(memberships) == 2
    assert {str(item.organization_id) for item in memberships} == {str(base_org_id), str(new_organization_id)}
    assert sum(1 for item in memberships if item.is_default) == 1
    assert any(str(item.organization_id) == str(base_org_id) and item.is_default for item in memberships)
    assert any(str(item.organization_id) == str(new_organization_id) and item.role == "admin" for item in memberships)
    assert str(user.organization_id) == str(base_org_id)


def test_admin_can_view_and_update_current_organization(client, db_session):
    onboard_response = client.post(
        "/organizations/onboard",
        json={
            "organization_name": "Complejo Centro",
            "admin_full_name": "Centro Admin",
            "admin_email": "centro@saas.com",
            "admin_password": "password123",
        },
    )
    assert onboard_response.status_code == 201
    admin_token = onboard_response.json()["access_token"]

    current_response = client.get("/organizations/current", headers=auth_headers(admin_token))
    assert current_response.status_code == 200
    assert current_response.json()["name"] == "Complejo Centro"

    update_response = client.patch(
        "/organizations/current",
        json={
          "name": "Complejo Centro Renovado",
          "slug": "centro-renovado",
        },
        headers=auth_headers(admin_token),
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Complejo Centro Renovado"
    assert update_response.json()["slug"] == "centro-renovado"


def test_public_request_context_exposes_branding_for_current_complex(client):
    onboard_response = client.post(
        "/organizations/onboard",
        json={
            "organization_name": "Complejo Branding Público",
            "organization_slug": "branding-publico",
            "admin_full_name": "Brand Admin",
            "admin_email": "brand-public@saas.com",
            "admin_password": "password123",
        },
    )
    assert onboard_response.status_code == 201
    admin_token = onboard_response.json()["access_token"]

    settings_response = client.patch(
        "/organizations/current/settings",
        json={
            "branding_name": "Branding Público",
            "logo_url": "https://example.com/logo.png",
            "primary_color": "#112233",
        },
        headers=auth_headers(admin_token),
    )
    assert settings_response.status_code == 200

    context_response = client.get("/organizations/request-context", headers=auth_headers(admin_token))
    assert context_response.status_code == 200
    payload = context_response.json()
    assert payload["organization"]["slug"] == "branding-publico"
    assert payload["branding_name"] == "Branding Público"
    assert payload["logo_url"] == "https://example.com/logo.png"
    assert payload["primary_color"] == "#112233"


def test_public_request_context_returns_404_for_unknown_slug(client):
    response = client.get(
        "/organizations/request-context",
        headers={"X-Organization-Slug": "slug-inexistente"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Complejo no encontrado"


def test_onboarding_creates_organization_settings_row(client, db_session):
    response = client.post(
        "/organizations/onboard",
        json={
            "organization_name": "Complejo Branding",
            "admin_full_name": "Brand Admin",
            "admin_email": "branding@saas.com",
            "admin_password": "password123",
        },
    )

    assert response.status_code == 201
    organization_id = response.json()["organization"]["id"]

    settings = db_session.get(OrganizationSettings, organization_id)
    assert settings is not None
    assert settings.branding_name == "Complejo Branding"


def test_admin_can_view_and_update_current_organization_settings(client):
    onboard_response = client.post(
        "/organizations/onboard",
        json={
            "organization_name": "Complejo Settings",
            "admin_full_name": "Settings Admin",
            "admin_email": "settings@saas.com",
            "admin_password": "password123",
        },
    )
    assert onboard_response.status_code == 201
    admin_token = onboard_response.json()["access_token"]

    current_response = client.get("/organizations/current/settings", headers=auth_headers(admin_token))
    assert current_response.status_code == 200
    assert current_response.json()["branding_name"] == "Complejo Settings"

    update_response = client.patch(
        "/organizations/current/settings",
        json={
            "branding_name": "Complejo Settings Pro",
            "primary_color": "#123456",
            "booking_min_lead_minutes": 45,
            "cancellation_min_lead_minutes": 180,
            "whatsapp_provider": "meta_cloud",
            "whatsapp_phone_number_id": "123456789",
            "whatsapp_template_language": "es_AR",
            "whatsapp_template_booking_confirmed": "booking_confirmed_org",
            "whatsapp_template_booking_cancelled": "booking_cancelled_org",
            "whatsapp_recipient_override": "+54 9 11 4455 6677",
        },
        headers=auth_headers(admin_token),
    )

    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["branding_name"] == "Complejo Settings Pro"
    assert payload["primary_color"] == "#123456"
    assert payload["booking_min_lead_minutes"] == 45
    assert payload["cancellation_min_lead_minutes"] == 180
    assert payload["whatsapp_provider"] == "meta_cloud"
    assert payload["whatsapp_phone_number_id"] == "123456789"
    assert payload["whatsapp_template_booking_confirmed"] == "booking_confirmed_org"
    assert payload["whatsapp_template_booking_cancelled"] == "booking_cancelled_org"
    assert payload["whatsapp_recipient_override"] == "5491144556677"


def test_staff_invitation_flow_creates_user_in_same_organization(client, db_session):
    onboard_response = client.post(
        "/organizations/onboard",
        json={
            "organization_name": "Complejo Staff",
            "admin_full_name": "Staff Admin",
            "admin_email": "staff-admin@saas.com",
            "admin_password": "password123",
        },
    )
    assert onboard_response.status_code == 201
    admin_token = onboard_response.json()["access_token"]
    organization_id = onboard_response.json()["organization"]["id"]

    create_response = client.post(
        "/organizations/current/staff-invitations",
        json={
            "email": "nuevo-staff@saas.com",
            "full_name": "Nuevo Staff",
            "role": "admin",
            "expires_in_days": 10,
        },
        headers=auth_headers(admin_token),
    )
    assert create_response.status_code == 201
    invitation_payload = create_response.json()
    assert invitation_payload["status"] == "pending"

    list_response = client.get("/organizations/current/staff-invitations", headers=auth_headers(admin_token))
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    accept_response = client.post(
        "/organizations/staff-invitations/accept",
        json={
            "token": invitation_payload["invite_token"],
            "full_name": "Nuevo Staff",
            "password": "password123",
            "whatsapp_number": "+54 9 11 2233 1122",
            "whatsapp_opt_in": True,
        },
    )
    assert accept_response.status_code == 200
    accepted_payload = accept_response.json()
    assert accepted_payload["organization"]["id"] == organization_id
    assert accepted_payload["access_token"]

    invited_user = db_session.query(User).filter(User.email == "nuevo-staff@saas.com").first()
    invitation = db_session.query(StaffInvitation).filter(StaffInvitation.email == "nuevo-staff@saas.com").first()
    assert invited_user is not None
    assert str(invited_user.organization_id) == organization_id
    assert invited_user.role == "admin"
    assert invited_user.whatsapp_number == "5491122331122"
    assert invitation is not None
    assert invitation.status == "accepted"
    assert invitation.accepted_at is not None
    membership = (
        db_session.query(OrganizationMembership)
        .filter(
            OrganizationMembership.user_id == invited_user.id,
            OrganizationMembership.organization_id == invitation.organization_id,
        )
        .first()
    )
    assert membership is not None
    assert membership.role == "admin"

    pending_after_accept_response = client.get(
        "/organizations/current/staff-invitations",
        headers=auth_headers(admin_token),
    )
    assert pending_after_accept_response.status_code == 200
    assert pending_after_accept_response.json() == []


def test_accepting_staff_invitation_cleans_other_pending_invites_for_same_email(client, db_session):
    onboard_response = client.post(
        "/organizations/onboard",
        json={
            "organization_name": "Complejo Staff Cleanup",
            "admin_full_name": "Cleanup Admin",
            "admin_email": "cleanup-admin@saas.com",
            "admin_password": "password123",
        },
    )
    assert onboard_response.status_code == 201
    admin_token = onboard_response.json()["access_token"]

    first_invite_response = client.post(
        "/organizations/current/staff-invitations",
        json={
            "email": "cleanup-staff@saas.com",
            "full_name": "Cleanup Staff",
            "role": "staff",
            "expires_in_days": 7,
        },
        headers=auth_headers(admin_token),
    )
    second_invite_response = client.post(
        "/organizations/current/staff-invitations",
        json={
            "email": "cleanup-staff@saas.com",
            "full_name": "Cleanup Staff",
            "role": "staff",
            "expires_in_days": 14,
        },
        headers=auth_headers(admin_token),
    )

    assert first_invite_response.status_code == 201
    assert second_invite_response.status_code == 201

    accept_response = client.post(
        "/organizations/staff-invitations/accept",
        json={
            "token": second_invite_response.json()["invite_token"],
            "full_name": "Cleanup Staff",
            "password": "password123",
        },
    )

    assert accept_response.status_code == 200

    remaining_pending = (
        db_session.query(StaffInvitation)
        .filter(
            StaffInvitation.email == "cleanup-staff@saas.com",
            StaffInvitation.status == "pending",
        )
        .count()
    )
    assert remaining_pending == 0


def test_accepting_staff_invitation_existing_account_adds_membership(client, db_session):
    owner_a = onboard_organization(
        client,
        organization_name="Complejo Invitador",
        organization_slug="complejo-invitador",
        admin_email="owner-invitador@saas.com",
    )
    owner_b = onboard_organization(
        client,
        organization_name="Complejo Receptor",
        organization_slug="complejo-receptor",
        admin_email="owner-receptor@saas.com",
    )
    invite_token = owner_b["access_token"]

    existing_user_token = register_and_login(client, "staff-existing@saas.com", "password123", "Staff Existing")
    existing_me = client.get("/auth/me", headers=auth_headers(existing_user_token))
    assert existing_me.status_code == 200
    original_org_id = existing_me.json()["organization_id"]

    invitation_response = client.post(
        "/organizations/current/staff-invitations",
        json={
            "email": "staff-existing@saas.com",
            "full_name": "Staff Existing",
            "role": "staff",
            "expires_in_days": 7,
        },
        headers=auth_headers(invite_token),
    )
    assert invitation_response.status_code == 201

    accept_response = client.post(
        "/organizations/staff-invitations/accept",
        json={
            "token": invitation_response.json()["invite_token"],
            "full_name": "Staff Existing",
            "password": "password123",
        },
    )
    assert accept_response.status_code == 200
    invited_org_id = accept_response.json()["organization"]["id"]

    existing_user = db_session.query(User).filter(User.email == "staff-existing@saas.com").first()
    memberships = (
        db_session.query(OrganizationMembership)
        .filter(OrganizationMembership.user_id == existing_user.id)
        .all()
    )
    assert len(memberships) == 2
    assert {str(item.organization_id) for item in memberships} == {str(original_org_id), str(invited_org_id)}
    assert str(existing_user.organization_id) == str(original_org_id)

    login_response = client.post(
        "/auth/login",
        data={"username": "staff-existing@saas.com", "password": "password123"},
        headers={"X-Organization-Slug": "complejo-receptor"},
    )
    assert login_response.status_code == 200
    me_response = client.get("/auth/me", headers=auth_headers(login_response.json()["access_token"]))
    assert me_response.status_code == 200
    assert me_response.json()["organization_slug"] == "complejo-receptor"
    assert me_response.json()["role"] == "staff"


def test_create_staff_invitation_reports_email_sent(client, monkeypatch):
    onboard = onboard_organization(
        client,
        organization_name="Complejo Mail",
        admin_email="mail-admin@saas.com",
    )
    admin_token = onboard["access_token"]

    monkeypatch.setattr(
        "app.api.routes.organizations.send_staff_invitation_email",
        lambda **kwargs: ("sent", "Invitación enviada por email correctamente."),
    )

    response = client.post(
        "/organizations/current/staff-invitations",
        json={
          "email": "staff-mail@saas.com",
          "full_name": "Staff Mail",
          "role": "staff",
          "expires_in_days": 7,
        },
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["email_delivery_status"] == "sent"
    assert payload["invite_url"].endswith(payload["invite_token"])


def test_create_staff_invitation_falls_back_to_manual_link_when_email_not_configured(client, monkeypatch):
    onboard = onboard_organization(
        client,
        organization_name="Complejo Manual",
        admin_email="manual-admin@saas.com",
    )
    admin_token = onboard["access_token"]

    monkeypatch.setattr(
        "app.api.routes.organizations.send_staff_invitation_email",
        lambda **kwargs: ("manual_required", "El correo automático no está configurado. Compartí el link manualmente."),
    )

    response = client.post(
        "/organizations/current/staff-invitations",
        json={
          "email": "staff-manual@saas.com",
          "full_name": "Staff Manual",
          "role": "staff",
          "expires_in_days": 7,
        },
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["email_delivery_status"] == "manual_required"


def test_admin_can_cancel_pending_staff_invitation(client, db_session):
    onboard = onboard_organization(
        client,
        organization_name="Complejo Cancel Invite",
        admin_email="cancel-admin@saas.com",
    )
    admin_token = onboard["access_token"]

    create_response = client.post(
        "/organizations/current/staff-invitations",
        json={
            "email": "cancel-staff@saas.com",
            "full_name": "Cancel Staff",
            "role": "staff",
            "expires_in_days": 7,
        },
        headers=auth_headers(admin_token),
    )
    assert create_response.status_code == 201
    invitation_id = create_response.json()["id"]

    cancel_response = client.delete(
        f"/organizations/current/staff-invitations/{invitation_id}",
        headers=auth_headers(admin_token),
    )

    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"

    pending_list_response = client.get(
        "/organizations/current/staff-invitations",
        headers=auth_headers(admin_token),
    )
    assert pending_list_response.status_code == 200
    assert pending_list_response.json() == []


def test_register_uses_requested_public_organization_slug(client, db_session):
    onboarding_response = client.post(
        "/organizations/onboard",
        json={
            "organization_name": "BlackPadel",
            "organization_slug": "blackpadel",
            "admin_full_name": "Black Admin",
            "admin_email": "black-admin@saas.com",
            "admin_password": "password123",
        },
    )
    assert onboarding_response.status_code == 201

    register_response = client.post(
        "/auth/register",
        json={
            "email": "jugador@blackpadel.com",
            "full_name": "Jugador BlackPadel",
            "password": "password123",
        },
        headers={"X-Organization-Slug": "blackpadel"},
    )

    assert register_response.status_code == 201
    payload = register_response.json()
    assert payload["organization_slug"] == "blackpadel"
    assert payload["organization_name"] == "BlackPadel"


def test_login_rejects_user_from_another_public_organization_slug(client):
    onboard_a = client.post(
        "/organizations/onboard",
        json={
            "organization_name": "Tenant A",
            "organization_slug": "tenant-a",
            "admin_full_name": "Admin A",
            "admin_email": "admin-a@saas.com",
            "admin_password": "password123",
        },
    )
    onboard_b = client.post(
        "/organizations/onboard",
        json={
            "organization_name": "Tenant B",
            "organization_slug": "tenant-b",
            "admin_full_name": "Admin B",
            "admin_email": "admin-b@saas.com",
            "admin_password": "password123",
        },
    )

    assert onboard_a.status_code == 201
    assert onboard_b.status_code == 201

    register_response = client.post(
        "/auth/register",
        json={
            "email": "usuario-a@saas.com",
            "full_name": "Usuario A",
            "password": "password123",
        },
        headers={"X-Organization-Slug": "tenant-a"},
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        data={
            "username": "usuario-a@saas.com",
            "password": "password123",
        },
        headers={"X-Organization-Slug": "tenant-b"},
    )

    assert login_response.status_code == 403
    assert login_response.json()["detail"] == "Esta cuenta pertenece a otro complejo"


def test_login_rejects_unknown_public_organization_slug(client):
    register_response = client.post(
        "/auth/register",
        json={
            "email": "usuario-unknown@saas.com",
            "full_name": "Usuario Unknown",
            "password": "password123",
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        data={
            "username": "usuario-unknown@saas.com",
            "password": "password123",
        },
        headers={"X-Organization-Slug": "slug-inexistente"},
    )

    assert login_response.status_code == 404
    assert login_response.json()["detail"] == "Complejo no encontrado"


def test_login_uses_requested_membership_as_active_context(client, db_session):
    org_a = Organization(name="Tenant Membership A", slug="tenant-membership-a", is_active=True)
    org_b = Organization(name="Tenant Membership B", slug="tenant-membership-b", is_active=True)
    db_session.add_all([org_a, org_b])
    db_session.flush()

    user = User(
        email="multi-org@example.com",
        full_name="Multi Org",
        hashed_password=get_password_hash("password123"),
        role="user",
        organization_id=org_a.id,
    )
    db_session.add(user)
    db_session.flush()

    db_session.add_all(
        [
            OrganizationMembership(
                user_id=user.id,
                organization_id=org_a.id,
                role="user",
                is_default=True,
            ),
            OrganizationMembership(
                user_id=user.id,
                organization_id=org_b.id,
                role="admin",
                is_default=False,
            ),
        ]
    )
    db_session.commit()

    login_response = client.post(
        "/auth/login",
        data={"username": "multi-org@example.com", "password": "password123"},
        headers={"X-Organization-Slug": "tenant-membership-b"},
    )

    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]

    me_response = client.get("/auth/me", headers=auth_headers(access_token))
    assert me_response.status_code == 200
    payload = me_response.json()
    assert payload["organization_slug"] == "tenant-membership-b"
    assert payload["role"] == "admin"
    assert payload["permissions"]["manage_organization"] is True

    admin_response = client.get("/admin/me", headers=auth_headers(access_token))
    assert admin_response.status_code == 200
    assert admin_response.json()["organization_slug"] == "tenant-membership-b"


def test_login_without_requested_slug_uses_default_membership(client, db_session):
    org_a = Organization(name="Tenant Default A", slug="tenant-default-a", is_active=True)
    org_b = Organization(name="Tenant Default B", slug="tenant-default-b", is_active=True)
    db_session.add_all([org_a, org_b])
    db_session.flush()

    user = User(
        email="default-membership@example.com",
        full_name="Default Membership",
        hashed_password=get_password_hash("password123"),
        role="user",
        organization_id=org_a.id,
    )
    db_session.add(user)
    db_session.flush()

    db_session.add_all(
        [
            OrganizationMembership(
                user_id=user.id,
                organization_id=org_a.id,
                role="staff",
                is_default=True,
            ),
            OrganizationMembership(
                user_id=user.id,
                organization_id=org_b.id,
                role="admin",
                is_default=False,
            ),
        ]
    )
    db_session.commit()

    login_response = client.post(
        "/auth/login",
        data={"username": "default-membership@example.com", "password": "password123"},
    )

    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]
    me_response = client.get("/auth/me", headers=auth_headers(access_token))
    assert me_response.status_code == 200
    payload = me_response.json()
    assert payload["organization_slug"] == "tenant-default-a"
    assert payload["role"] == "staff"
    assert payload["permissions"]["manage_organization"] is False
    assert len(payload["memberships"]) == 2
    assert any(item["organization_slug"] == "tenant-default-a" and item["is_active"] for item in payload["memberships"])
    assert any(item["organization_slug"] == "tenant-default-b" and not item["is_active"] for item in payload["memberships"])


def test_access_token_rejects_removed_membership_context(client, db_session):
    org_a = Organization(name="Tenant Token A", slug="tenant-token-a", is_active=True)
    org_b = Organization(name="Tenant Token B", slug="tenant-token-b", is_active=True)
    db_session.add_all([org_a, org_b])
    db_session.flush()

    user = User(
        email="removed-membership@example.com",
        full_name="Removed Membership",
        hashed_password=get_password_hash("password123"),
        role="user",
        organization_id=org_a.id,
    )
    db_session.add(user)
    db_session.flush()

    removable_membership = OrganizationMembership(
        user_id=user.id,
        organization_id=org_b.id,
        role="admin",
        is_default=False,
    )
    db_session.add_all(
        [
            OrganizationMembership(
                user_id=user.id,
                organization_id=org_a.id,
                role="user",
                is_default=True,
            ),
            removable_membership,
        ]
    )
    db_session.commit()

    login_response = client.post(
        "/auth/login",
        data={"username": "removed-membership@example.com", "password": "password123"},
        headers={"X-Organization-Slug": "tenant-token-b"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]
    refresh_token = login_response.json()["refresh_token"]

    db_session.delete(removable_membership)
    db_session.commit()

    me_response = client.get("/auth/me", headers=auth_headers(access_token))
    assert me_response.status_code == 403
    assert me_response.json()["detail"] == "Esta cuenta pertenece a otro complejo"

    refresh_response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_response.status_code == 403
    assert refresh_response.json()["detail"] == "Esta cuenta pertenece a otro complejo"


def test_switch_organization_changes_active_membership_context(client, db_session):
    org_a = Organization(name="Tenant Switch A", slug="tenant-switch-a", is_active=True)
    org_b = Organization(name="Tenant Switch B", slug="tenant-switch-b", is_active=True)
    db_session.add_all([org_a, org_b])
    db_session.flush()

    user = User(
        email="switch-membership@example.com",
        full_name="Switch Membership",
        hashed_password=get_password_hash("password123"),
        role="user",
        organization_id=org_a.id,
    )
    db_session.add(user)
    db_session.flush()

    db_session.add_all(
        [
            OrganizationMembership(
                user_id=user.id,
                organization_id=org_a.id,
                role="user",
                is_default=True,
            ),
            OrganizationMembership(
                user_id=user.id,
                organization_id=org_b.id,
                role="admin",
                is_default=False,
            ),
        ]
    )
    db_session.commit()

    login_response = client.post(
        "/auth/login",
        data={"username": "switch-membership@example.com", "password": "password123"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]

    switch_response = client.post(
        "/auth/switch-organization",
        json={"organization_id": str(org_b.id)},
        headers=auth_headers(access_token),
    )
    assert switch_response.status_code == 200

    me_response = client.get("/auth/me", headers=auth_headers(switch_response.json()["access_token"]))
    assert me_response.status_code == 200
    payload = me_response.json()
    assert payload["organization_slug"] == "tenant-switch-b"
    assert payload["role"] == "admin"
    assert any(item["organization_slug"] == "tenant-switch-b" and item["is_active"] for item in payload["memberships"])


def test_switched_admin_can_create_timeslots_in_active_organization(client, db_session):
    sport = Sport(name="Tenis switch", description="Cambio de tenant")
    db_session.add(sport)
    db_session.commit()
    db_session.refresh(sport)

    owner_a = onboard_organization(
        client,
        organization_name="Complejo Switch A",
        organization_slug="complejo-switch-a",
        admin_email="owner-switch-a@saas.com",
    )
    owner_b = onboard_organization(
        client,
        organization_name="Complejo Switch B",
        organization_slug="complejo-switch-b",
        admin_email="owner-switch-b@saas.com",
    )

    first_org_id = owner_a["organization"]["id"]
    second_org_id = owner_b["organization"]["id"]
    owner_user = db_session.query(User).filter(User.email == "owner-switch-a@saas.com").first()
    second_org = db_session.get(Organization, second_org_id)
    ensure_membership(
        db_session,
        user=owner_user,
        organization=second_org,
        role="admin",
        make_default=False,
    )
    db_session.commit()

    venue_response = client.post(
        "/venues",
        json={
            "name": "Sede Switch B",
            "address": "Calle B 123",
            "timezone": "America/Argentina/Buenos_Aires",
            "allowed_sport_id": str(sport.id),
        },
        headers=auth_headers(owner_b["access_token"]),
    )
    assert venue_response.status_code == 201

    court_response = client.post(
        "/courts",
        json={
            "venue_id": venue_response.json()["id"],
            "sport_id": str(sport.id),
            "name": "Cancha Switch B",
            "indoor": False,
            "is_active": True,
        },
        headers=auth_headers(owner_b["access_token"]),
    )
    assert court_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        data={"username": "owner-switch-a@saas.com", "password": "password123"},
    )
    assert login_response.status_code == 200
    switch_response = client.post(
        "/auth/switch-organization",
        json={"organization_id": second_org_id},
        headers=auth_headers(login_response.json()["access_token"]),
    )
    assert switch_response.status_code == 200

    create_response = client.post(
        "/timeslots",
        json={
            "court_id": court_response.json()["id"],
            "starts_at": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
            "ends_at": (datetime.now(timezone.utc) + timedelta(days=3, hours=1)).isoformat(),
            "capacity": 4,
            "price": 18000,
            "is_active": True,
        },
        headers=auth_headers(switch_response.json()["access_token"]),
    )
    assert create_response.status_code == 201
    assert create_response.json()["court_id"] == court_response.json()["id"]

    first_org_timeslots = db_session.query(TimeSlot).filter(TimeSlot.organization_id == first_org_id).all()
    second_org_timeslots = db_session.query(TimeSlot).filter(TimeSlot.organization_id == second_org_id).all()
    assert len(first_org_timeslots) == 0
    assert len(second_org_timeslots) == 1


def test_switched_admin_bulk_create_timeslots_in_active_organization(client, db_session):
    sport = Sport(name="Padel switch bulk", description="Cambio bulk")
    db_session.add(sport)
    db_session.commit()
    db_session.refresh(sport)

    owner_a = onboard_organization(
        client,
        organization_name="Complejo Bulk A",
        organization_slug="complejo-bulk-a",
        admin_email="owner-bulk-a@saas.com",
    )
    owner_b = onboard_organization(
        client,
        organization_name="Complejo Bulk B",
        organization_slug="complejo-bulk-b",
        admin_email="owner-bulk-b@saas.com",
    )

    owner_user = db_session.query(User).filter(User.email == "owner-bulk-a@saas.com").first()
    second_org = db_session.get(Organization, owner_b["organization"]["id"])
    ensure_membership(
        db_session,
        user=owner_user,
        organization=second_org,
        role="admin",
        make_default=False,
    )
    db_session.commit()

    venue_response = client.post(
        "/venues",
        json={
            "name": "Sede Bulk B",
            "address": "Calle Bulk 456",
            "timezone": "America/Argentina/Buenos_Aires",
            "allowed_sport_id": str(sport.id),
        },
        headers=auth_headers(owner_b["access_token"]),
    )
    assert venue_response.status_code == 201

    court_response = client.post(
        "/courts",
        json={
            "venue_id": venue_response.json()["id"],
            "sport_id": str(sport.id),
            "name": "Cancha Bulk B",
            "indoor": True,
            "is_active": True,
        },
        headers=auth_headers(owner_b["access_token"]),
    )
    assert court_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        data={"username": "owner-bulk-a@saas.com", "password": "password123"},
    )
    assert login_response.status_code == 200
    switch_response = client.post(
        "/auth/switch-organization",
        json={"organization_id": owner_b["organization"]["id"]},
        headers=auth_headers(login_response.json()["access_token"]),
    )
    assert switch_response.status_code == 200

    base_day = datetime.now(timezone.utc).replace(hour=18, minute=0, second=0, microsecond=0) + timedelta(days=4)
    bulk_response = client.post(
        "/admin/timeslots/bulk",
        json={
            "court_ids": [court_response.json()["id"]],
            "window_starts_at": base_day.isoformat(),
            "window_ends_at": (base_day + timedelta(hours=2)).isoformat(),
            "slot_minutes": 60,
            "capacity": 4,
            "price": 18000,
            "is_active": True,
        },
        headers=auth_headers(switch_response.json()["access_token"]),
    )
    assert bulk_response.status_code == 201
    assert bulk_response.json()["created_count"] == 2

    current_timeslots_response = client.get(
        "/timeslots",
        params={
            "court_id": court_response.json()["id"],
            "date_from": base_day.isoformat(),
            "date_to": (base_day + timedelta(days=1)).isoformat(),
        },
        headers=auth_headers(switch_response.json()["access_token"]),
    )
    assert current_timeslots_response.status_code == 200
    assert len(current_timeslots_response.json()) == 2


def test_bulk_create_ignores_conflicts_from_other_organization_rows(client, db_session):
    sport = Sport(name="Padel bulk mismatch", description="Mismatch org")
    db_session.add(sport)
    db_session.commit()
    db_session.refresh(sport)

    owner_a = onboard_organization(
        client,
        organization_name="Complejo Mismatch A",
        organization_slug="complejo-mismatch-a",
        admin_email="owner-mismatch-a@saas.com",
    )
    owner_b = onboard_organization(
        client,
        organization_name="Complejo Mismatch B",
        organization_slug="complejo-mismatch-b",
        admin_email="owner-mismatch-b@saas.com",
    )

    venue_response = client.post(
        "/venues",
        json={
            "name": "Sede Mismatch B",
            "address": "Calle Mismatch 456",
            "timezone": "America/Argentina/Buenos_Aires",
            "allowed_sport_id": str(sport.id),
        },
        headers=auth_headers(owner_b["access_token"]),
    )
    assert venue_response.status_code == 201

    court_response = client.post(
        "/courts",
        json={
            "venue_id": venue_response.json()["id"],
            "sport_id": str(sport.id),
            "name": "Cancha Mismatch B",
            "indoor": True,
            "is_active": True,
        },
        headers=auth_headers(owner_b["access_token"]),
    )
    assert court_response.status_code == 201

    base_day = datetime.now(timezone.utc).replace(hour=18, minute=0, second=0, microsecond=0) + timedelta(days=4)
    malformed_timeslot = TimeSlot(
        organization_id=owner_a["organization"]["id"],
        court_id=court_response.json()["id"],
        starts_at=base_day,
        ends_at=base_day + timedelta(hours=1),
        capacity=4,
        price=18000,
        is_active=True,
    )
    db_session.add(malformed_timeslot)
    db_session.commit()

    bulk_response = client.post(
        "/admin/timeslots/bulk",
        json={
            "court_ids": [court_response.json()["id"]],
            "window_starts_at": base_day.isoformat(),
            "window_ends_at": (base_day + timedelta(hours=1)).isoformat(),
            "slot_minutes": 60,
            "capacity": 4,
            "price": 18000,
            "is_active": True,
        },
        headers=auth_headers(owner_b["access_token"]),
    )
    assert bulk_response.status_code == 201
    assert bulk_response.json()["created_count"] == 1
    assert bulk_response.json()["skipped_count"] == 0

    tenant_b_timeslots = (
        db_session.query(TimeSlot)
        .filter(
            TimeSlot.organization_id == owner_b["organization"]["id"],
            TimeSlot.court_id == court_response.json()["id"],
        )
        .all()
    )
    assert len(tenant_b_timeslots) == 1


def test_inactive_organization_blocks_public_context_and_registration(client):
    onboard_response = client.post(
        "/organizations/onboard",
        json={
            "organization_name": "BlackPadel Suspendido",
            "organization_slug": "blackpadel-suspendido",
            "admin_full_name": "Black Admin",
            "admin_email": "black-suspendido-admin@saas.com",
            "admin_password": "password123",
        },
    )
    assert onboard_response.status_code == 201
    admin_token = onboard_response.json()["access_token"]

    deactivate_response = client.patch(
        "/organizations/current",
        json={"is_active": False},
        headers=auth_headers(admin_token),
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False

    context_response = client.get(
        "/organizations/request-context",
        headers={"X-Organization-Slug": "blackpadel-suspendido"},
    )
    assert context_response.status_code == 403
    assert context_response.json()["detail"] == "Este complejo está desactivado"

    register_response = client.post(
        "/auth/register",
        json={
            "email": "jugador-suspendido@saas.com",
            "full_name": "Jugador Suspendido",
            "password": "password123",
        },
        headers={"X-Organization-Slug": "blackpadel-suspendido"},
    )
    assert register_response.status_code == 403
    assert register_response.json()["detail"] == "Este complejo está desactivado"


def test_inactive_organization_blocks_user_session_but_admin_can_still_access(client):
    onboard_response = client.post(
        "/organizations/onboard",
        json={
            "organization_name": "Complejo Inactivo",
            "organization_slug": "complejo-inactivo",
            "admin_full_name": "Owner Inactivo",
            "admin_email": "owner-inactivo@saas.com",
            "admin_password": "password123",
        },
    )
    assert onboard_response.status_code == 201
    admin_token = onboard_response.json()["access_token"]

    register_response = client.post(
        "/auth/register",
        json={
            "email": "usuario-inactivo@saas.com",
            "full_name": "Usuario Inactivo",
            "password": "password123",
        },
        headers={"X-Organization-Slug": "complejo-inactivo"},
    )
    assert register_response.status_code == 201

    user_login_response = client.post(
        "/auth/login",
        data={"username": "usuario-inactivo@saas.com", "password": "password123"},
        headers={"X-Organization-Slug": "complejo-inactivo"},
    )
    assert user_login_response.status_code == 200
    user_token = user_login_response.json()["access_token"]

    deactivate_response = client.patch(
        "/organizations/current",
        json={"is_active": False},
        headers=auth_headers(admin_token),
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False

    blocked_me_response = client.get("/auth/me", headers=auth_headers(user_token))
    assert blocked_me_response.status_code == 403
    assert blocked_me_response.json()["detail"] == "Este complejo está desactivado"

    blocked_login_response = client.post(
        "/auth/login",
        data={"username": "usuario-inactivo@saas.com", "password": "password123"},
        headers={"X-Organization-Slug": "complejo-inactivo"},
    )
    assert blocked_login_response.status_code == 403
    assert blocked_login_response.json()["detail"] == "Este complejo está desactivado"

    admin_login_response = client.post(
        "/auth/login",
        data={"username": "owner-inactivo@saas.com", "password": "password123"},
        headers={"X-Organization-Slug": "complejo-inactivo"},
    )
    assert admin_login_response.status_code == 200

    current_org_response = client.get(
        "/organizations/current",
        headers=auth_headers(admin_login_response.json()["access_token"]),
    )
    assert current_org_response.status_code == 200
    assert current_org_response.json()["is_active"] is False


def test_booking_policies_use_organization_defaults_when_sport_has_no_override(client):
    onboard_response = client.post(
        "/organizations/onboard",
        json={
            "organization_name": "Complejo Policy",
            "admin_full_name": "Policy Admin",
            "admin_email": "policy-admin@saas.com",
            "admin_password": "password123",
        },
    )
    assert onboard_response.status_code == 201
    admin_token = onboard_response.json()["access_token"]

    update_response = client.patch(
        "/organizations/current/settings",
        json={
            "booking_min_lead_minutes": 75,
            "cancellation_min_lead_minutes": 210,
        },
        headers=auth_headers(admin_token),
    )
    assert update_response.status_code == 200

    policy_response = client.get("/bookings/policies", headers=auth_headers(admin_token))
    assert policy_response.status_code == 200
    payload = policy_response.json()
    assert payload["uses_default_policy"] is True
    assert payload["min_booking_lead_minutes"] == 75
    assert payload["cancellation_min_lead_minutes"] == 210
    assert payload["admin_summary"] == "Política general del complejo."


def test_admin_notification_status_uses_tenant_level_whatsapp_settings(client):
    onboard_response = client.post(
        "/organizations/onboard",
        json={
            "organization_name": "Complejo WhatsApp",
            "admin_full_name": "WhatsApp Admin",
            "admin_email": "whatsapp-admin@saas.com",
            "admin_password": "password123",
        },
    )
    assert onboard_response.status_code == 201
    admin_token = onboard_response.json()["access_token"]

    update_response = client.patch(
        "/organizations/current/settings",
        json={
            "whatsapp_provider": "meta_cloud",
            "whatsapp_access_token": "tenant-token",
            "whatsapp_phone_number_id": "tenant-phone-id",
            "whatsapp_template_language": "es_AR",
            "whatsapp_template_booking_confirmed": "tenant_booking_ok",
            "whatsapp_template_booking_cancelled": "tenant_booking_cancel",
            "whatsapp_recipient_override": "+54 9 11 6677 8899",
        },
        headers=auth_headers(admin_token),
    )
    assert update_response.status_code == 200

    status_response = client.get("/admin/notification-status", headers=auth_headers(admin_token))
    assert status_response.status_code == 200
    payload = status_response.json()
    assert payload["provider"] == "meta_cloud"
    assert payload["configured"] is True
    assert payload["ready_for_live_send"] is True
    assert payload["booking_confirmed_template"] == "tenant_booking_ok"
    assert payload["booking_cancelled_template"] == "tenant_booking_cancel"
    assert payload["recipient_override"] == "5491166778899"


def test_admin_holidays_returns_monthly_calendar(client, db_session, monkeypatch):
    register_and_login(client, "holiday-admin@example.com", "password123", "Holiday Admin")
    admin_user = db_session.query(User).filter(User.email == "holiday-admin@example.com").first()
    admin_user.role = "admin"
    db_session.commit()

    admin_token = client.post(
        "/auth/login",
        data={"username": "holiday-admin@example.com", "password": "password123"},
    ).json()["access_token"]

    monkeypatch.setattr(
        "app.api.routes.admin.fetch_public_holidays",
        lambda year, country_code: [
            HolidayRecord(
                date="2026-04-02",
                local_name="Día del Veterano",
                name="Malvinas Day",
                country_code=country_code,
                global_holiday=True,
                counties=None,
                launch_year=None,
                types=["Public"],
            ),
            HolidayRecord(
                date="2026-05-01",
                local_name="Día del Trabajador",
                name="Labour Day",
                country_code=country_code,
                global_holiday=True,
                counties=None,
                launch_year=None,
                types=["Public"],
            ),
        ],
    )

    response = client.get("/admin/holidays?year=2026&month=4&country_code=AR", headers=auth_headers(admin_token))
    assert response.status_code == 200
    payload = response.json()
    assert payload["country_code"] == "AR"
    assert payload["year"] == 2026
    assert payload["month"] == 4
    assert len(payload["holidays"]) == 1
    assert payload["holidays"][0]["date"] == "2026-04-02"


def test_admin_holidays_surfaces_provider_failures(client, db_session, monkeypatch):
    register_and_login(client, "holiday-fail-admin@example.com", "password123", "Holiday Fail Admin")
    admin_user = db_session.query(User).filter(User.email == "holiday-fail-admin@example.com").first()
    admin_user.role = "admin"
    db_session.commit()

    admin_token = client.post(
        "/auth/login",
        data={"username": "holiday-fail-admin@example.com", "password": "password123"},
    ).json()["access_token"]

    monkeypatch.setattr(
        "app.api.routes.admin.fetch_public_holidays",
        lambda year, country_code: (_ for _ in ()).throw(HolidayProviderError("Proveedor caído")),
    )

    response = client.get("/admin/holidays?year=2026&country_code=AR", headers=auth_headers(admin_token))
    assert response.status_code == 502
    assert response.json()["detail"] == "Proveedor caído"


def test_admin_can_create_global_sport_and_enable_it_for_current_organization(client):
    onboard_response = client.post(
        "/organizations/onboard",
        json={
            "organization_name": "Complejo Deportes",
            "admin_full_name": "Deportes Admin",
            "admin_email": "deportes-admin@saas.com",
            "admin_password": "password123",
        },
    )
    assert onboard_response.status_code == 201
    admin_token = onboard_response.json()["access_token"]

    create_response = client.post(
        "/sports",
        json={
            "name": "Pilates",
            "description": "Clases con cupos por cama",
            "booking_min_lead_minutes": 60,
            "cancellation_min_lead_minutes": 180,
        },
        headers=auth_headers(admin_token),
    )
    assert create_response.status_code == 201
    created_sport = create_response.json()
    assert created_sport["name"] == "Pilates"

    enabled_response = client.get("/organizations/current/sports", headers=auth_headers(admin_token))
    assert enabled_response.status_code == 200
    enabled_sports = enabled_response.json()
    assert any(item["sport"]["name"] == "Pilates" and item["is_enabled"] for item in enabled_sports)

    public_response = client.get("/sports", headers=auth_headers(admin_token))
    assert public_response.status_code == 200
    assert any(item["name"] == "Pilates" for item in public_response.json())


def test_admin_can_upload_organization_logo(client, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "MEDIA_STORAGE_BACKEND", "local")
    monkeypatch.setattr(settings, "MEDIA_ROOT", str(tmp_path / "uploads"))

    onboard_response = client.post(
        "/organizations/onboard",
        json={
            "organization_name": "Complejo Logo",
            "admin_full_name": "Logo Admin",
            "admin_email": "logo-admin@saas.com",
            "admin_password": "password123",
        },
    )
    assert onboard_response.status_code == 201
    admin_token = onboard_response.json()["access_token"]
    organization_id = onboard_response.json()["organization"]["id"]

    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc`\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    response = client.post(
        "/organizations/current/logo",
        headers=auth_headers(admin_token),
        files={"file": ("logo.png", png_bytes, "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["logo_url"].startswith(f"/media/organization-logos/{organization_id}/")
    relative_path = payload["logo_url"].removeprefix("/media/")
    assert (tmp_path / "uploads" / relative_path).exists()


def test_admin_can_upload_organization_logo_to_external_storage(client, monkeypatch):
    from app.core.config import settings

    uploaded_objects = []
    deleted_objects = []

    class FakeS3Client:
        def put_object(self, **kwargs):
            uploaded_objects.append(kwargs)

        def delete_object(self, **kwargs):
            deleted_objects.append(kwargs)

    monkeypatch.setattr(settings, "MEDIA_STORAGE_BACKEND", "s3")
    monkeypatch.setattr(settings, "S3_BUCKET_NAME", "sports-booking-assets")
    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", "https://cdn.example.com")
    monkeypatch.setattr(settings, "S3_ENDPOINT_URL", "https://example.r2.cloudflarestorage.com")
    monkeypatch.setattr(settings, "S3_REGION", "auto")
    monkeypatch.setattr(settings, "S3_ACCESS_KEY_ID", "key")
    monkeypatch.setattr(settings, "S3_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setattr(settings, "S3_KEY_PREFIX", "production")
    monkeypatch.setattr("app.core.logo_storage.get_s3_client", lambda: FakeS3Client())

    onboard_response = client.post(
        "/organizations/onboard",
        json={
            "organization_name": "Complejo Logo Externo",
            "admin_full_name": "Logo Admin",
            "admin_email": "logo-externo@saas.com",
            "admin_password": "password123",
        },
    )
    assert onboard_response.status_code == 201
    admin_token = onboard_response.json()["access_token"]
    organization_id = onboard_response.json()["organization"]["id"]

    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc`\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    response = client.post(
        "/organizations/current/logo",
        headers=auth_headers(admin_token),
        files={"file": ("logo.png", png_bytes, "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["logo_url"].startswith("https://cdn.example.com/production/organization-logos/")
    assert f"/{organization_id}/" in payload["logo_url"]
    assert len(uploaded_objects) == 1
    assert uploaded_objects[0]["Bucket"] == "sports-booking-assets"
    assert uploaded_objects[0]["ContentType"] == "image/png"
    assert deleted_objects == []


def test_admin_readiness_reflects_operational_setup(client, db_session):
    sport = Sport(name="Pilates Readiness", description="Clases")
    db_session.add(sport)
    db_session.commit()

    onboard_response = client.post(
        "/organizations/onboard",
        json={
            "organization_name": "Complejo Ready",
            "admin_full_name": "Ready Admin",
            "admin_email": "ready-admin@saas.com",
            "admin_password": "password123",
        },
    )
    assert onboard_response.status_code == 201
    admin_token = onboard_response.json()["access_token"]
    organization_id = onboard_response.json()["organization"]["id"]

    initial_response = client.get("/admin/readiness", headers=auth_headers(admin_token))
    assert initial_response.status_code == 200
    initial_payload = initial_response.json()
    assert initial_payload["summary"]["is_ready"] is False
    assert "WhatsApp operativo" in initial_payload["summary"]["missing_items"]
    assert "Sedes cargadas" in initial_payload["summary"]["missing_items"]

    settings = db_session.query(OrganizationSettings).filter(OrganizationSettings.organization_id == organization_id).first()
    settings.logo_url = "/media/organization-logos/mock/logo.png"
    settings.primary_color = "#112233"
    settings.booking_min_lead_minutes = 30
    settings.cancellation_min_lead_minutes = 120
    settings.whatsapp_provider = "meta_cloud"
    settings.whatsapp_access_token = "token"
    settings.whatsapp_phone_number_id = "phone-id"
    settings.whatsapp_template_language = "es_AR"
    settings.whatsapp_template_booking_confirmed = "booking_ok"
    settings.whatsapp_template_booking_cancelled = "booking_cancel"
    db_session.add(settings)
    db_session.flush()

    venue = Venue(
        name="Sede Ready",
        address="Lista 123",
        timezone="America/Argentina/Buenos_Aires",
        allowed_sport_id=sport.id,
        organization_id=organization_id,
    )
    db_session.add(venue)
    db_session.flush()

    court = Court(
        venue_id=venue.id,
        sport_id=sport.id,
        name="Sala 1",
        indoor=True,
        is_active=True,
        organization_id=organization_id,
    )
    db_session.add(court)
    db_session.flush()

    starts_at = datetime.now(timezone.utc) + timedelta(days=3)
    timeslot = TimeSlot(
        court_id=court.id,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
        capacity=8,
        price=15000,
        is_active=True,
        organization_id=organization_id,
    )
    db_session.add(timeslot)
    db_session.commit()

    ready_response = client.get("/admin/readiness", headers=auth_headers(admin_token))
    assert ready_response.status_code == 200
    ready_payload = ready_response.json()
    assert ready_payload["summary"]["is_ready"] is True
    assert ready_payload["summary"]["readiness_percent"] == 100
    assert ready_payload["summary"]["missing_items"] == []


def test_admin_audit_events_capture_sensitive_actions(client, db_session):
    onboard_response = client.post(
        "/organizations/onboard",
        json={
            "organization_name": "Complejo Audit",
            "organization_slug": "complejo-audit",
            "admin_full_name": "Audit Admin",
            "admin_email": "audit-admin@saas.com",
            "admin_password": "password123",
        },
    )
    assert onboard_response.status_code == 201
    admin_token = onboard_response.json()["access_token"]

    update_org_response = client.patch(
        "/organizations/current",
        json={"name": "Complejo Audit Norte", "is_active": False},
        headers=auth_headers(admin_token),
    )
    assert update_org_response.status_code == 200

    invitation_response = client.post(
        "/organizations/current/staff-invitations",
        json={
            "email": "audit-staff@saas.com",
            "full_name": "Audit Staff",
            "role": "staff",
            "expires_in_days": 7,
        },
        headers=auth_headers(admin_token),
    )
    assert invitation_response.status_code == 201

    audit_response = client.get("/admin/audit-events", headers=auth_headers(admin_token))
    assert audit_response.status_code == 200
    payload = audit_response.json()
    assert any(event["action"] == "organization.updated" for event in payload)
    assert any(event["action"] == "staff.invitation.created" for event in payload)

    stored_events = (
        db_session.query(AdminAuditEvent)
        .filter(AdminAuditEvent.organization_id == onboard_response.json()["organization"]["id"])
        .order_by(AdminAuditEvent.created_at.desc())
        .all()
    )
    assert len(stored_events) >= 2

