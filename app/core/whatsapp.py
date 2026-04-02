import logging
import re
from typing import Any

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

WHATSAPP_DISABLED_DETAIL = "Notificaciones de WhatsApp deshabilitadas"
WHATSAPP_NOT_CONFIGURED_DETAIL = "La integración de WhatsApp todavía no está configurada"


def normalize_whatsapp_number(value: str | None) -> str | None:
    if value is None:
        return None
    digits = re.sub(r"[^\d+]", "", value.strip())
    if not digits:
        return None
    if digits.startswith("+"):
        return digits[1:]
    return digits


def whatsapp_is_enabled() -> bool:
    return settings.WHATSAPP_PROVIDER == "meta_cloud"


def whatsapp_is_configured() -> bool:
    return bool(
        whatsapp_is_enabled()
        and settings.WHATSAPP_ACCESS_TOKEN
        and settings.WHATSAPP_PHONE_NUMBER_ID
    )


def notification_status_payload() -> dict[str, Any]:
    has_access_token = bool(settings.WHATSAPP_ACCESS_TOKEN)
    has_phone_number_id = bool(settings.WHATSAPP_PHONE_NUMBER_ID)
    has_booking_confirmed_template = bool(settings.WHATSAPP_TEMPLATE_BOOKING_CONFIRMED)
    has_booking_cancelled_template = bool(settings.WHATSAPP_TEMPLATE_BOOKING_CANCELLED)
    recipient_override = settings.WHATSAPP_RECIPIENT_OVERRIDE
    enabled = whatsapp_is_enabled()
    configured = whatsapp_is_configured()
    ready_for_live_send = bool(
        enabled
        and configured
        and has_booking_confirmed_template
        and has_booking_cancelled_template
    )

    checks = [
        {
            "key": "provider",
            "label": "Proveedor Meta Cloud activo",
            "ok": enabled,
            "detail": "Seleccioná WHATSAPP_PROVIDER=meta_cloud para habilitar el canal real.",
            "severity": "required",
        },
        {
            "key": "access_token",
            "label": "Access token cargado",
            "ok": has_access_token,
            "detail": "Hace falta WHATSAPP_ACCESS_TOKEN para autenticar los envíos.",
            "severity": "required",
        },
        {
            "key": "phone_number_id",
            "label": "Phone number ID configurado",
            "ok": has_phone_number_id,
            "detail": "Hace falta WHATSAPP_PHONE_NUMBER_ID para apuntar al número emisor.",
            "severity": "required",
        },
        {
            "key": "booking_confirmed_template",
            "label": "Template de confirmación definido",
            "ok": has_booking_confirmed_template,
            "detail": "Cargá WHATSAPP_TEMPLATE_BOOKING_CONFIRMED con el nombre aprobado en Meta.",
            "severity": "required",
        },
        {
            "key": "booking_cancelled_template",
            "label": "Template de cancelación definido",
            "ok": has_booking_cancelled_template,
            "detail": "Cargá WHATSAPP_TEMPLATE_BOOKING_CANCELLED con el nombre aprobado en Meta.",
            "severity": "required",
        },
        {
            "key": "recipient_override",
            "label": "Número override para pruebas",
            "ok": bool(recipient_override),
            "detail": "Opcional. Úsalo para testear sin enviar al cliente final.",
            "severity": "optional",
        },
    ]

    missing_items = [check["label"] for check in checks if check["severity"] == "required" and not check["ok"]]

    return {
        "provider": settings.WHATSAPP_PROVIDER,
        "enabled": enabled,
        "configured": configured,
        "ready_for_live_send": ready_for_live_send,
        "has_access_token": has_access_token,
        "has_phone_number_id": has_phone_number_id,
        "recipient_override": recipient_override,
        "template_language": settings.WHATSAPP_TEMPLATE_LANGUAGE,
        "booking_confirmed_template": settings.WHATSAPP_TEMPLATE_BOOKING_CONFIRMED,
        "booking_cancelled_template": settings.WHATSAPP_TEMPLATE_BOOKING_CANCELLED,
        "has_booking_confirmed_template": has_booking_confirmed_template,
        "has_booking_cancelled_template": has_booking_cancelled_template,
        "test_mode": bool(recipient_override),
        "missing_items": missing_items,
        "checks": checks,
    }


def send_whatsapp_template(*, to: str, template_name: str, body_parameters: list[str]) -> bool:
    if not whatsapp_is_enabled():
        logger.info("WhatsApp skip: provider disabled")
        return False

    if not whatsapp_is_configured():
        logger.warning("WhatsApp skip: provider selected but not configured")
        return False

    recipient = normalize_whatsapp_number(settings.WHATSAPP_RECIPIENT_OVERRIDE or to)
    if not recipient:
        logger.warning("WhatsApp skip: recipient missing or invalid")
        return False

    try:
        response = requests.post(
            f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages",
            headers={
                "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "to": recipient,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": settings.WHATSAPP_TEMPLATE_LANGUAGE},
                    "components": [
                        {
                            "type": "body",
                            "parameters": [{"type": "text", "text": value} for value in body_parameters],
                        }
                    ],
                },
            },
            timeout=15,
        )
    except requests.RequestException as exc:
        logger.warning("WhatsApp send raised an exception: %s", exc)
        return False

    if response.ok:
        logger.info("WhatsApp notification sent to %s using template %s", recipient, template_name)
        return True

    logger.warning(
        "WhatsApp send failed with status %s: %s",
        response.status_code,
        response.text,
    )
    return False
