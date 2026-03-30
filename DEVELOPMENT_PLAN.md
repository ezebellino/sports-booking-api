# Development Plan

## Product Goal
Build a mobile-first sports booking experience that lets a user register, browse sports venues, pick courts and timeslots, and confirm bookings with minimal friction.

## Current Baseline
- FastAPI backend with auth, sports, venues, courts, timeslots, and bookings.
- React + Tailwind frontend scaffold in `frontend/`.
- Local auth flow with persistent session and booking UI.
- CORS enabled for local frontend development.

## Guiding Principles
- Keep the user flow mobile-first from day one.
- Prioritize end-to-end usable slices over isolated screens.
- Avoid adding backend complexity unless it unlocks clear UX gains.
- Version every meaningful checkpoint.

## Phase 1: Solid MVP
Objective: make booking usable and reliable for a normal user.

### Frontend
- Polish responsive navigation and spacing for small screens.
- Improve loading, empty, success, and error states.
- Add simple field validation and better feedback in auth forms.
- Surface clearer venue, court, and timeslot details.

### Backend
- Keep current endpoints stable.
- Add richer booking payloads or supporting read endpoints where UI friction is high.
- Standardize error messages for frontend display.

### QA
- Verify register, login, explore, reserve, and bookings flows manually.
- Smoke test build and backend startup on every checkpoint.

## Phase 2: Operations and Admin
Objective: make the system maintainable by an operator.

### Admin Features
- Admin login or role-aware access.
- CRUD views for sports, venues, courts, and timeslots.
- Better filtering by sport, venue, and date.

### Backend Support
- Introduce roles and permissions.
- Add safer validation around inactive courts and expired timeslots.
- Add pagination and query ergonomics where needed.

## Phase 3: Booking Quality
Objective: make the reservation domain production-friendlier.

- Cancellation flow.
- Occupancy and availability indicators.
- Anti-overbooking hardening.
- Reservation history and status transitions.
- Timezone clarity across venues and users.

## Phase 4: Business Layer
Objective: prepare the app for monetization and real operations.

- Payments integration.
- Booking policies and cancellation windows.
- Notifications by email or WhatsApp.
- Metrics dashboard for demand, occupancy, and revenue.

## Immediate Next Sprint
1. Improve the explore page UX and booking confirmation states.
2. Add backend-friendly booking detail responses for the frontend.
3. Create an admin module for timeslot management.
4. Define role model and protected admin routes.
5. Add basic automated tests for auth and booking flows.

## Definition of Done for Each Iteration
- The flow works end-to-end locally.
- Mobile layout is reviewed first.
- Build passes in frontend.
- Backend imports and startup checks pass.
- Changes are committed with a clear message.
