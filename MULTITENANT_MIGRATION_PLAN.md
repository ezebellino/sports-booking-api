# Multi-Tenant Migration Plan

## Goal
Move Sports Booking from a single-complex architecture to a SaaS-ready multi-tenant model using a shared database with tenant scoping.

## Target Model
- One application instance.
- One shared database.
- Each sports complex is represented as an `organization`.
- All operational data is isolated by `organization_id`.

## Why This Approach
- Keeps infrastructure simple.
- Avoids one-database-per-client complexity too early.
- Matches the current maturity of the project.
- Lets us evolve toward billing, plans, and branded customer spaces later.

## Current State
- The app behaves as single-tenant.
- Core entities do not yet belong to an organization.
- Admin and user access is role-based, but not tenant-scoped.
- WhatsApp, metrics, inventory, bookings, and timeslots are global to the current dataset.

## Migration Principles
- Do the migration in small, reversible slices.
- Prefer compatibility layers over big-bang refactors.
- Backfill existing data into one default organization first.
- Do not introduce billing or pricing tiers before tenant isolation is complete.
- Keep auth simple at first: one user belongs to one organization.

## Phase MT1: Foundation
Objective: introduce the tenant entity without breaking current flows.

### Task MT1.1
Create `organizations` table.

Suggested fields:
- `id`
- `name`
- `slug`
- `is_active`
- `created_at`
- `updated_at`

### Task MT1.2
Add `organization_id` to:
- `users`
- `venues`
- `courts`
- `timeslots`
- `bookings`

Notes:
- Start nullable only if needed for the migration window.
- End state should be `NOT NULL` on operational tables.

### Task MT1.3
Create one default organization for current data.

Suggested seed:
- name: `Complejo Demo`
- slug: `complejo-demo`

### Task MT1.4
Backfill all existing rows to that default organization.

Definition of done:
- Every existing user, venue, court, timeslot, and booking has an `organization_id`.

## Phase MT2: Domain Integrity
Objective: ensure relationships stay inside the same tenant.

### Task MT2.1
Update SQLAlchemy models and relationships to include `organization_id`.

### Task MT2.2
Enforce tenant consistency in write flows.

Examples:
- a booking cannot reference a timeslot from another organization
- a court cannot be assigned to a venue from another organization
- a timeslot cannot be created for a court from another organization

### Task MT2.3
Review unique constraints and indexes for tenant-aware behavior.

Examples:
- venue names may need uniqueness per organization, not globally
- emails may stay globally unique for now, or be revisited later depending on product decision

Definition of done:
- Cross-tenant writes are rejected.
- Core uniqueness rules are compatible with SaaS usage.

## Phase MT3: Auth and Access Scope
Objective: make every authenticated request tenant-aware.

### Task MT3.1
Attach `organization_id` to the authenticated user context.

### Task MT3.2
Create a shared dependency/helper for tenant-scoped queries.

### Task MT3.3
Filter backend routes by `organization_id`.

Priority order:
1. admin inventory
2. admin timeslots
3. bookings
4. timeslots listing
5. sports and policies where applicable
6. metrics
7. WhatsApp operational endpoints

Definition of done:
- Admins only see data from their organization.
- Users only interact with data from their organization.

## Phase MT4: Frontend Tenant Awareness
Objective: reflect tenant context cleanly in the UI without adding unnecessary complexity.

### Task MT4.1
Expose organization data in `/auth/me`.

Suggested fields:
- `organization_id`
- `organization_name`
- `organization_slug`

### Task MT4.2
Show organization name in admin and user shell.

### Task MT4.3
Review navigation and empty states so they read as “your complex” instead of a global system.

Definition of done:
- The UI makes it clear which complex the user is operating inside.

## Phase MT5: Tenant-Level Configuration
Objective: move operational settings from global app config to tenant-owned config where appropriate.

Candidates:
- booking policy defaults
- cancellation policy defaults
- WhatsApp sender config
- branding
- timezone defaults

Important:
- Do this after tenant isolation is stable.
- Do not move everything at once.

## Phase MT6: Optional Future Evolution
Objective: prepare for more advanced SaaS scenarios later.

Possible later additions:
- memberships table for users belonging to multiple organizations
- owner/admin/operator roles per organization
- invite flows
- subscription plans
- custom domains or white-labeling

## Safe Execution Order
1. Create `organizations`
2. Add `organization_id`
3. Backfill existing data
4. Update models
5. Scope backend queries
6. Expose tenant in auth payload
7. Update frontend shell
8. Move config to tenant level

## Risks To Watch
- Cross-tenant data leaks in list endpoints
- Existing unique constraints blocking real SaaS adoption
- Orphan records during backfill
- Bookings tied to timeslots from a different organization
- Admin metrics mixing multiple complexes
- Notification settings remaining global by mistake

## Definition of Done
- All core operational tables have `organization_id`
- Existing data is backfilled
- Backend reads and writes are tenant-scoped
- Auth exposes tenant context
- Frontend reflects tenant context
- Metrics and notifications are isolated per organization
- Tests cover tenant boundaries for critical flows

## Recommended Next Step
Start with MT1.1 and MT1.2:
- create the `organizations` model and migration
- add `organization_id` to core entities
- backfill current data into one default organization
