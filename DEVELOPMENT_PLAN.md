# Development Plan

## Product Goal
Build a mobile-first sports booking experience that lets a user register, browse sports venues, pick courts and timeslots, and confirm bookings with minimal friction.

## Current Baseline
- FastAPI backend with auth, sports, venues, courts, timeslots, and bookings.
- React + Tailwind frontend scaffold in `frontend/`.
- Local auth flow with persistent session and booking UI.
- CORS enabled for local frontend development.
- Role model with `admin` and `user`.
- Admin timeslot module with bulk generation, inline editing, duplicate-aware preview, and richer availability signals.
- Automated backend coverage for auth, booking, cancellations, occupancy, and admin timeslot generation.

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

## Sprint 01 Status
Objective: turn the scaffold into a reliable MVP slice with a cleaner booking flow and a clear path to admin capabilities.

### Completed
- Task A1: Explore flow improved for mobile with sticky context and stronger selected states.
- Task A2: Auth and booking feedback improved with clearer validation and outcome states.
- Task B1: `GET /bookings` now returns nested sport, venue, court, and timeslot details.
- Task B2: Auth and booking errors are now standardized for frontend display.
- Task C1: Role model defined with protected admin routes and role-aware navigation.
- Task C2: First admin timeslot module shipped with bulk create, edit, and duplicate-aware preview.
- Task D1: Automated checks cover auth, booking, admin protection, and bulk timeslot generation.

### Still Useful To Formalize
- Task D2: Keep a repeatable release checklist attached to every checkpoint.

## Release Checklist
- Frontend build passes.
- Backend tests pass.
- Manual review of Home, Explore, Bookings, and Admin Timeslots on mobile-first layout.
- UTF-8 review for visible UI strings after edits done from Windows shell.
- Commit and push after a coherent product slice is complete.

## Sprint 02 Status
Objective: move from "usable admin slice" to "operable platform" for real daily management.

### Completed
- Task A1: Admin CRUD for venues and courts shipped in-app.
- Task A2: Admin filtering improved across inventory and timeslots.
- Task B1: Cancellation flow added with status history and capacity release.
- Task B2: Explore now surfaces occupancy, remaining spots, and full / few spots left states.

### Remaining

#### Track C: Domain Safety
Priority: P2

Task C1: Add safer validation for inactive and expired resources.
- Prevent booking on inactive courts and expired timeslots consistently.
- Ensure admin edits do not create invalid states silently.
Done when:
- Invalid operational states are blocked with readable errors.

Task C2: Improve timezone clarity.
- Make venue-local time explicit in admin and user views.
- Avoid confusion around late-night slots and UTC serialization.
Done when:
- Operators and users interpret displayed schedules the same way.

## Recommended Next Task
Start with Sprint 02 / Track C / Task C1: add safer validation for inactive and expired resources.
Reason:
- It closes a domain safety gap now that reservation and admin flows are already more complete.
- It aligns backend rules with the new availability signals shown in Explore.
- It prevents confusing edge cases before we move into booking policies and monetization.

## Definition of Done for Each Iteration
- The flow works end-to-end locally.
- Mobile layout is reviewed first.
- Frontend build passes.
- Backend tests pass when backend behavior changed.
- Visible strings are checked for UTF-8 correctness.
- Changes are committed with a clear message.

