from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.organization_membership import OrganizationMembership
from app.models.user import User


def ensure_membership(
    db: Session,
    *,
    user: User,
    organization: Organization,
    role: str,
    make_default: bool = False,
) -> OrganizationMembership:
    existing_membership = (
        db.query(OrganizationMembership)
        .filter(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == organization.id,
        )
        .first()
    )

    if existing_membership:
        existing_membership.role = role
        membership = existing_membership
    else:
        membership = OrganizationMembership(
            user_id=user.id,
            organization_id=organization.id,
            role=role,
            is_default=False,
        )
        db.add(membership)
        db.flush()

    has_other_memberships = (
        db.query(OrganizationMembership)
        .filter(OrganizationMembership.user_id == user.id, OrganizationMembership.organization_id != organization.id)
        .count()
        > 0
    )
    if make_default or not has_other_memberships:
        (
            db.query(OrganizationMembership)
            .filter(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.organization_id != organization.id,
                OrganizationMembership.is_default.is_(True),
            )
            .update({"is_default": False}, synchronize_session=False)
        )
        membership.is_default = True
    elif existing_membership is None:
        membership.is_default = False

    db.add(membership)
    db.flush()
    return membership
