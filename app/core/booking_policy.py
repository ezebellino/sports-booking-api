from dataclasses import dataclass

from app.core.config import settings
from app.models.sport import Sport
from app.models.timeslot import TimeSlot


@dataclass(frozen=True)
class ResolvedBookingPolicy:
    sport_id: str | None
    sport_name: str | None
    min_booking_lead_minutes: int
    cancellation_min_lead_minutes: int
    uses_default_policy: bool


def resolve_policy_for_sport(sport: Sport | None) -> ResolvedBookingPolicy:
    booking_minutes = settings.BOOKING_MIN_LEAD_MINUTES
    cancellation_minutes = settings.CANCELLATION_MIN_LEAD_MINUTES
    uses_default_policy = True

    if sport is not None:
        if sport.booking_min_lead_minutes is not None:
            booking_minutes = sport.booking_min_lead_minutes
            uses_default_policy = False
        if sport.cancellation_min_lead_minutes is not None:
            cancellation_minutes = sport.cancellation_min_lead_minutes
            uses_default_policy = False

    return ResolvedBookingPolicy(
        sport_id=str(sport.id) if sport is not None else None,
        sport_name=sport.name if sport is not None else None,
        min_booking_lead_minutes=booking_minutes,
        cancellation_min_lead_minutes=cancellation_minutes,
        uses_default_policy=uses_default_policy,
    )


def resolve_policy_for_timeslot(timeslot: TimeSlot) -> ResolvedBookingPolicy:
    sport = None
    if timeslot.court is not None:
        sport = timeslot.court.sport
    return resolve_policy_for_sport(sport)


def booking_policy_message(policy: ResolvedBookingPolicy) -> str:
    if policy.sport_name:
        return (
            f"Las reservas de {policy.sport_name} deben hacerse con al menos "
            f"{policy.min_booking_lead_minutes} minutos de anticipación."
        )
    return (
        f"Las reservas deben hacerse con al menos "
        f"{policy.min_booking_lead_minutes} minutos de anticipación."
    )


def cancellation_policy_message(policy: ResolvedBookingPolicy) -> str:
    if policy.sport_name:
        return (
            f"Las cancelaciones de {policy.sport_name} se permiten hasta "
            f"{policy.cancellation_min_lead_minutes} minutos antes del inicio del turno."
        )
    return (
        f"Las cancelaciones se permiten hasta "
        f"{policy.cancellation_min_lead_minutes} minutos antes del inicio del turno."
    )


def policy_source_message(policy: ResolvedBookingPolicy) -> str:
    if policy.sport_name and not policy.uses_default_policy:
        return f"Esta configuración específica aplica al deporte {policy.sport_name}."
    if policy.sport_name:
        return f"{policy.sport_name} usa la política general del complejo."
    return "Política general del complejo."
