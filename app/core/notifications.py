import logging
from datetime import datetime

from app.core.config import settings
from app.core.whatsapp import send_whatsapp_template
from app.models.booking import Booking

logger = logging.getLogger(__name__)


def _format_start(booking: Booking) -> str:
    venue_timezone = booking.timeslot.court.venue.timezone
    localized = booking.timeslot.starts_at.astimezone(datetime.now().astimezone().tzinfo)
    try:
        from zoneinfo import ZoneInfo
        localized = booking.timeslot.starts_at.astimezone(ZoneInfo(venue_timezone))
    except Exception:
        pass
    return localized.strftime("%d/%m %H:%M")


def send_booking_confirmed_notification(booking: Booking) -> bool:
    user = booking.user
    if not user.whatsapp_opt_in or not user.whatsapp_number:
        return False

    return send_whatsapp_template(
        to=user.whatsapp_number,
        template_name=settings.WHATSAPP_TEMPLATE_BOOKING_CONFIRMED,
        body_parameters=[
            user.full_name or user.email,
            booking.timeslot.court.sport.name,
            booking.timeslot.court.venue.name,
            booking.timeslot.court.name,
            _format_start(booking),
        ],
    )


def send_booking_cancelled_notification(booking: Booking) -> bool:
    user = booking.user
    if not user.whatsapp_opt_in or not user.whatsapp_number:
        return False

    return send_whatsapp_template(
        to=user.whatsapp_number,
        template_name=settings.WHATSAPP_TEMPLATE_BOOKING_CANCELLED,
        body_parameters=[
            user.full_name or user.email,
            booking.timeslot.court.sport.name,
            booking.timeslot.court.venue.name,
            booking.timeslot.court.name,
            _format_start(booking),
        ],
    )
