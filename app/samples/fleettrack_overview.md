# FleetTrack: technical security overview

FleetTrack is a business-to-business service that lets a client company track its own drivers and vehicles for logistics. It is a FastAPI backend with a SQLite database and one read-only, server-rendered dashboard for fleet managers. It is multi-tenant: each client company sees only its own drivers, vehicles and trips. FleetTrack processes driver data on behalf of its client companies, and it is also the controller for its own platform account and audit data.

## Parts of the system

- The FleetTrack API (app/main.py and app/routers/) handles sign-in, roles, driver and vehicle records, telemetry ingestion, trips and reports.
- The FleetTrack database is a SQLite file, fleettrack.db, accessed through SQLAlchemy models in app/models.py.
- The FleetTrack dashboard (app/routers/dashboard.py) is a server-rendered page for the Fleet Manager role only.
- A telemetry simulator (scripts/simulate_telemetry.py) stands in for the in-vehicle devices.

## Accounts and access

There are four account types: fleet manager, driver, system administrator and tenant owner, defined in app/models.py and enforced by require_roles() in app/rbac.py. Tenant owners and fleet managers can register themselves against an existing company; drivers and system administrators are created by an administrator script (scripts/seed.py).

Every request passes the same chain of checks in app/rbac.py: get_current_user() verifies the sign-in token, require_roles() rejects a user whose role is not allowed, and require_same_company() rejects a user from a different company unless they are a system administrator. The dashboard reuses these same checks. We tested that a fleet manager from one company who opens another company's trip-history address directly is refused.

Users sign in through POST /auth/login and receive a signed token (HS256, PyJWT, app/auth.py); requests without a valid token get a 401 response. Passwords are hashed with bcrypt through passlib (app/security.py), and no password is stored in plain text.

## Audit logging

write_audit_log() in app/audit.py records the user, action, record type, record id and time for every create, update and delete of drivers and vehicles, and for every read of trips, reports and the dashboard's last-known locations. The log entry is written in the same database transaction as the change, so the two cannot disagree. We tested that creating, updating and deleting one driver produced exactly three log entries with the right user. There is no screen for reviewing the log yet; it can be queried directly from the audit_log table.

## Personal data handling

Every driver record must state its lawful basis for processing; the API refuses to create a driver without it, and the database column cannot be empty. The default recorded at onboarding is that processing is necessary for the employment relationship.

Location telemetry is accepted only from a signed-in driver, for the driver's own assigned vehicle and company, so nothing is collected beyond the logistics purpose. The same data is also used for driver performance reports; there is no mechanism yet that checks whether this second use is compatible with the first.

Drivers' and vehicles' identity details can be corrected by a fleet manager of the same company through PUT /drivers/{id} and PUT /vehicles/{id}. Corrections are made by hand on request; there is no automatic check for out-of-date details.

Each trip has a retention date 90 days after it ends. purge_expired_telemetry() in app/trips.py deletes the detailed location points of expired trips and keeps the trip summary. We tested that it removes only the expired trip's points. It is not yet run on a schedule.

## Known gaps

- Encryption in transit is not implemented. The service runs over plain HTTP in development, and no TLS termination exists. A reverse proxy with TLS is planned for production but has not been built or tested.
- Encryption at rest is not implemented. fleettrack.db is an unencrypted file on local disk.
- There is no incident response plan and no formal incident or breach reporting procedure. The audit log could support detecting an incident, but no alerting or reporting process has been built on it.
- No data protection impact assessment has been carried out, although the system continuously monitors driver locations.
- There is no written data protection management programme: no data inventory, complaints process, review schedule or named oversight role.
- A mapping vendor and an overseas cloud host are assumed for future versions; neither arrangement exists today.
