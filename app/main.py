from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import health, auth
from app.api.routes import sports, venues, courts, timeslots, bookings
from app.api.routes import organizations
from app.api.routes import admin
from app.core.config import settings

app = FastAPI(title="Sports Booking API", version="0.2.0")

allowed_origins = [origin.strip() for origin in settings.FRONTEND_ORIGINS.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(organizations.router)
app.include_router(sports.router)
app.include_router(venues.router)
app.include_router(courts.router)
app.include_router(timeslots.router)
app.include_router(bookings.router)
app.include_router(admin.router)
