from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.organization_settings import OrganizationSettings


def get_or_create_organization_settings(db: Session, organization: Organization) -> OrganizationSettings:
    settings = organization.settings
    if settings:
        return settings

    settings = OrganizationSettings(organization_id=organization.id)
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings
