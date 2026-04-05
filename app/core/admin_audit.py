from typing import Any

from sqlalchemy.orm import Session

from app.models.admin_audit_event import AdminAuditEvent


def record_admin_audit_event(
    db: Session,
    *,
    organization_id,
    actor_user_id,
    action: str,
    target_type: str,
    summary: str,
    target_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> AdminAuditEvent:
    event = AdminAuditEvent(
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        summary=summary,
        details=details,
    )
    db.add(event)
    return event
