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
