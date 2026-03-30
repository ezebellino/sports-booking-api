from datetime import datetime, timedelta, timezone

from app.models.court import Court
from app.models.sport import Sport
from app.models.timeslot import TimeSlot
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

    login_response = client.post("/auth/login", data={"username": email, "password": password})
    assert login_response.status_code == 200

    tokens = login_response.json()
    assert tokens["access_token"]
    assert tokens["refresh_token"]
    assert tokens["token_type"] == "bearer"

    me_response = client.get("/auth/me", headers=auth_headers(tokens["access_token"]))
    assert me_response.status_code == 200
    assert me_response.json()["full_name"] == "Player One"

    refresh_response = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh_response.status_code == 200
    assert refresh_response.json()["access_token"]
    assert refresh_response.json()["refresh_token"]


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
    assert second_response.json()["detail"] == "Timeslot is full"