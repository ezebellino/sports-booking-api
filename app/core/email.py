from email.message import EmailMessage
from smtplib import SMTP, SMTPException

from app.core.config import settings


def email_is_configured() -> bool:
    return bool(
        settings.EMAIL_PROVIDER == "smtp"
        and settings.EMAIL_FROM
        and settings.SMTP_HOST
        and settings.SMTP_USERNAME
        and settings.SMTP_PASSWORD
    )


def build_staff_invitation_link(token: str) -> str:
    return f"{settings.FRONTEND_PUBLIC_URL.rstrip('/')}/accept-invite?token={token}"


def send_staff_invitation_email(
    *,
    recipient_email: str,
    recipient_name: str | None,
    organization_name: str,
    inviter_name: str | None,
    role: str,
    invite_token: str,
) -> tuple[str, str]:
    invite_link = build_staff_invitation_link(invite_token)

    if not email_is_configured():
        return (
            "manual_required",
            "El correo automático no está configurado. Compartí el link manualmente.",
        )

    message = EmailMessage()
    sender_name = settings.EMAIL_FROM_NAME or "Sports Booking"
    message["From"] = f"{sender_name} <{settings.EMAIL_FROM}>"
    message["To"] = recipient_email
    message["Subject"] = f"Invitación a {organization_name}"

    addressed_name = recipient_name or recipient_email
    inviter_label = inviter_name or "el equipo administrador"
    role_label = {"admin": "admin", "staff": "staff", "user": "usuario"}.get(role, role)

    text_body = (
        f"Hola {addressed_name},\n\n"
        f"{inviter_label} te invitó a sumarte a {organization_name} con el rol {role_label}.\n\n"
        f"Aceptá la invitación desde este link:\n{invite_link}\n\n"
        "Si no esperabas este correo, simplemente ignoralo.\n"
    )
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #0f172a;">
        <h2>Invitación a {organization_name}</h2>
        <p>Hola {addressed_name},</p>
        <p>{inviter_label} te invitó a sumarte a <strong>{organization_name}</strong> con el rol <strong>{role_label}</strong>.</p>
        <p>
          <a href="{invite_link}" style="display:inline-block;padding:12px 18px;background:#0f172a;color:#ffffff;text-decoration:none;border-radius:12px;">
            Aceptar invitación
          </a>
        </p>
        <p>Si el botón no funciona, copiá y pegá este enlace:</p>
        <p>{invite_link}</p>
        <p>Si no esperabas este correo, simplemente ignoralo.</p>
      </body>
    </html>
    """.strip()

    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    try:
        with SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as smtp:
            if settings.SMTP_USE_TLS:
                smtp.starttls()
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(message)
    except SMTPException as exc:
        return ("failed", f"No se pudo enviar el email automático: {exc}")
    except OSError as exc:
        return ("failed", f"No se pudo conectar al servidor SMTP: {exc}")

    return ("sent", "Invitación enviada por email correctamente.")
