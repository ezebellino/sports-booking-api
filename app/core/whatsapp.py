import logging
import re
from typing import Any

import requests

from app.core.config import settings
from app.models.organization_settings import OrganizationSettings

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


def resolve_whatsapp_config(organization_settings: OrganizationSettings | None = None) -> dict[str, Any]:
    provider = (
        organization_settings.whatsapp_provider
        if organization_settings and organization_settings.whatsapp_provider
        else settings.WHATSAPP_PROVIDER
    )
    access_token = (
        organization_settings.whatsapp_access_token
        if organization_settings and organization_settings.whatsapp_access_token
        else settings.WHATSAPP_ACCESS_TOKEN
    )
    phone_number_id = (
        organization_settings.whatsapp_phone_number_id
        if organization_settings and organization_settings.whatsapp_phone_number_id
        else settings.WHATSAPP_PHONE_NUMBER_ID
    )
    template_language = (
        organization_settings.whatsapp_template_language
        if organization_settings and organization_settings.whatsapp_template_language
        else settings.WHATSAPP_TEMPLATE_LANGUAGE
    )
    booking_confirmed_template = (
        organization_settings.whatsapp_template_booking_confirmed
        if organization_settings and organization_settings.whatsapp_template_booking_confirmed
        else settings.WHATSAPP_TEMPLATE_BOOKING_CONFIRMED
    )
    booking_cancelled_template = (
        organization_settings.whatsapp_template_booking_cancelled
        if organization_settings and organization_settings.whatsapp_template_booking_cancelled
        else settings.WHATSAPP_TEMPLATE_BOOKING_CANCELLED
    )
    recipient_override = (
        organization_settings.whatsapp_recipient_override
        if organization_settings and organization_settings.whatsapp_recipient_override
        else settings.WHATSAPP_RECIPIENT_OVERRIDE
    )
    enabled = provider == "meta_cloud"
    configured = bool(enabled and access_token and phone_number_id)

    return {
        "provider": provider,
        "enabled": enabled,
        "configured": configured,
        "access_token": access_token,
        "phone_number_id": phone_number_id,
        "template_language": template_language,
        "booking_confirmed_template": booking_confirmed_template,
        "booking_cancelled_template": booking_cancelled_template,
        "recipient_override": recipient_override,
    }


def notification_status_payload(organization_settings: OrganizationSettings | None = None) -> dict[str, Any]:
    config = resolve_whatsapp_config(organization_settings)
    has_access_token = bool(config["access_token"])
    has_phone_number_id = bool(config["phone_number_id"])
    has_booking_confirmed_template = bool(config["booking_confirmed_template"])
    has_booking_cancelled_template = bool(config["booking_cancelled_template"])
    recipient_override = config["recipient_override"]
    enabled = config["enabled"]
    configured = config["configured"]
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
            "detail": "Seleccioná provider=meta_cloud para habilitar el canal real.",
            "severity": "required",
        },
        {
            "key": "access_token",
            "label": "Access token cargado",
            "ok": has_access_token,
            "detail": "Hace falta un access token para autenticar los envíos.",
            "severity": "required",
        },
        {
            "key": "phone_number_id",
            "label": "Phone number ID configurado",
            "ok": has_phone_number_id,
            "detail": "Hace falta el phone number ID para apuntar al número emisor.",
            "severity": "required",
        },
        {
            "key": "booking_confirmed_template",
            "label": "Template de confirmación definido",
            "ok": has_booking_confirmed_template,
            "detail": "Cargá el template aprobado para confirmación de reserva.",
            "severity": "required",
        },
        {
            "key": "booking_cancelled_template",
            "label": "Template de cancelación definido",
            "ok": has_booking_cancelled_template,
            "detail": "Cargá el template aprobado para cancelación de reserva.",
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
        "provider": config["provider"],
        "enabled": enabled,
        "configured": configured,
        "ready_for_live_send": ready_for_live_send,
        "has_access_token": has_access_token,
        "has_phone_number_id": has_phone_number_id,
        "recipient_override": recipient_override,
        "template_language": config["template_language"],
        "booking_confirmed_template": config["booking_confirmed_template"],
        "booking_cancelled_template": config["booking_cancelled_template"],
        "has_booking_confirmed_template": has_booking_confirmed_template,
        "has_booking_cancelled_template": has_booking_cancelled_template,
        "test_mode": bool(recipient_override),
        "missing_items": missing_items,
        "checks": checks,
    }


def send_whatsapp_template(
    *,
    to: str,
    template_name: str,
    body_parameters: list[str],
    organization_settings: OrganizationSettings | None = None,
) -> bool:
    config = resolve_whatsapp_config(organization_settings)

    if not config["enabled"]:
        logger.info("WhatsApp skip: provider disabled")
        return False

    if not config["configured"]:
        logger.warning("WhatsApp skip: provider selected but not configured")
        return False

    recipient = normalize_whatsapp_number(config["recipient_override"] or to)
    if not recipient:
        logger.warning("WhatsApp skip: recipient missing or invalid")
        return False

    try:
        response = requests.post(
            f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{config['phone_number_id']}/messages",
            headers={
                "Authorization": f"Bearer {config['access_token']}",
                "Content-Type": "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "to": recipient,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": config["template_language"]},
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
