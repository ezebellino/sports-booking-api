from fastapi import FastAPI
from app.api.routes import health, auth
from app.api.routes import sports, venues, courts, timeslots, bookings

app = FastAPI(title="Sports Booking API", version="0.2.0")

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(sports.router)
app.include_router(venues.router)
app.include_router(courts.router)
app.include_router(timeslots.router)
app.include_router(bookings.router)
