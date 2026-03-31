from datetime import datetime, timedelta, timezone

from app.models.court import Court
from app.models.sport import Sport
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


def seed_timeslot(db_session, *, capacity: int = 1) -> TimeSlot:
    sport = Sport(name="Padel", description="Partidos rápidos")
    db_session.add(sport)
    db_session.flush()

    venue = Venue(
        name="Complejo Norte",
        address="Av. Siempre Viva 123",
        timezone="America/Argentina/Buenos_Aires",
        allowed_sport_id=sport.id,
    )
    db_session.add(venue)
    db_session.flush()

    court = Court(
        venue_id=venue.id,
        sport_id=sport.id,
        name="Cancha 1",
        indoor=True,
        is_active=True,
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

    refresh_response = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh_response.status_code == 200
    assert refresh_response.json()["access_token"]
    assert refresh_response.json()["refresh_token"]


def test_admin_route_requires_admin_role(client, db_session):
    user_token = register_and_login(client, "normal@example.com", "password123", "Normal User")
    forbidden_response = client.get("/admin/me", headers=auth_headers(user_token))
    assert forbidden_response.status_code == 403
    assert forbidden_response.json()["detail"] == "Acceso exclusivo para administradores"

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
    assert delete_court_response.json()["detail"] == "No se puede eliminar una cancha con turnos asociados"

    delete_venue_response = client.delete(
        f"/venues/{timeslot.court.venue_id}",
        headers=auth_headers(admin_token),
    )
    assert delete_venue_response.status_code == 409
    assert delete_venue_response.json()["detail"] == "No se puede eliminar una sede con canchas asociadas"


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
