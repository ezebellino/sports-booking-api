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

## Sprint 01 Backlog
Objective: turn the current scaffold into a reliable MVP slice with a cleaner booking flow and a clear path to admin capabilities.

### Track A: UX and Product Flow
Priority: P1

Task A1: Improve the explore flow on mobile.
- Add stronger selected states and sticky context for chosen sport, venue, and court.
- Make timeslot cards easier to scan with clearer date, price, and venue labels.
- Prevent accidental dead ends by guiding the user when a previous filter is missing.
Done when:
- A user can move from sport to confirmed booking without confusion on a mobile viewport.

Task A2: Improve auth and booking feedback.
- Add inline validation for login and register forms.
- Differentiate loading, success, and error messages more clearly.
- Reset stale success messages when filters or actions change.
Done when:
- Login, register, and reserve actions always show a clear outcome state.

### Track B: Backend Read Models
Priority: P1

Task B1: Add booking detail responses for the frontend.
- Expand booking reads so the frontend does not need to reconstruct venue, court, and sport context from multiple endpoints.
- Keep the existing create booking flow stable.
Done when:
- `GET /bookings` returns enough data to render a booking card directly.

Task B2: Standardize API-facing error messages.
- Review auth and booking errors for consistent `detail` payloads.
- Make user-facing failures readable and predictable.
Done when:
- Frontend can show backend errors without custom parsing per endpoint.

### Track C: Admin Foundation
Priority: P2

Task C1: Define roles and admin protection strategy.
- Decide the first role model: `admin` and `user`.
- Protect admin-only routes in backend and frontend navigation.
Done when:
- There is a clear technical rule for what an admin can access.

Task C2: Build the first admin timeslot module.
- Create an admin screen to list and create timeslots.
- Keep scope narrow: start with create + list before full edit/delete UX.
Done when:
- An admin can create a timeslot from the frontend and see it reflected in the system.

### Track D: Confidence and QA
Priority: P1

Task D1: Add automated checks for auth and booking flows.
- Cover register or login success path.
- Cover booking creation success path.
- Cover at least one booking failure case, such as duplicate booking or full timeslot.
Done when:
- Core auth and booking flows have repeatable test coverage.

Task D2: Add a release checklist for each checkpoint.
- Frontend build passes.
- Backend import or startup checks pass.
- Manual mobile review is completed.
Done when:
- Each milestone can be validated the same way before commit.

## Recommended Execution Order
1. Task B1: booking detail responses.
2. Task A1: improve explore flow using the richer booking shape.
3. Task A2: auth and booking feedback polish.
4. Task D1: automated tests for the current slice.
5. Task C1: define roles.
6. Task C2: admin timeslot module.

## Next Task To Start
Start with Task B1.
Reason:
- It removes frontend join workarounds.
- It improves the current user-facing bookings screen immediately.
- It creates a cleaner contract before we keep polishing the UI.

## Definition of Done for Each Iteration
- The flow works end-to-end locally.
- Mobile layout is reviewed first.
- Build passes in frontend.
- Backend imports and startup checks pass.
- Changes are committed with a clear message.
