from pydantic import BaseModel


class AdminMetricsBucket(BaseModel):
    name: str
    total_timeslots: int
    active_timeslots: int
    confirmed_bookings: int
    cancelled_bookings: int
    spots_total: int
    spots_filled: int
    occupancy_rate: float
    cancellation_rate: float
    estimated_revenue: float


class AdminMetricsSummary(BaseModel):
    date_from: str | None = None
    date_to: str | None = None
    total_timeslots: int
    active_timeslots: int
    upcoming_timeslots: int
    confirmed_bookings: int
    cancelled_bookings: int
    spots_total: int
    spots_filled: int
    occupancy_rate: float
    cancellation_rate: float
    estimated_revenue: float


class AdminMetricsPublic(BaseModel):
    summary: AdminMetricsSummary
    by_sport: list[AdminMetricsBucket]
    by_venue: list[AdminMetricsBucket]


class TenantIntegrityCounts(BaseModel):
    organizations: int
    users_without_organization: int
    venues_without_organization: int
    courts_without_organization: int
    timeslots_without_organization: int
    bookings_without_organization: int


class TenantIntegrityIssues(BaseModel):
    court_venue_mismatches: int
    timeslot_court_mismatches: int
    booking_user_mismatches: int
    booking_timeslot_mismatches: int


class TenantIntegrityPublic(BaseModel):
    counts: TenantIntegrityCounts
    issues: TenantIntegrityIssues
    ready_for_not_null: bool
