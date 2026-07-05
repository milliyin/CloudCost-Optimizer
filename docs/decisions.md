# Decision Notes

## 2026-06-27 - Vite chosen for frontend scaffolding

Vite is the current recommended React scaffolding path for a lightweight client
app, and it keeps Stage 0 fast to understand and demo.

## 2026-06-27 - PostgreSQL provisioned from day one

The project prompt expects relational data with migrations and auditability.
Provisioning Postgres in Stage 0 keeps the local stack aligned with the later
stages instead of swapping databases midstream.

## 2026-06-29 - PyJWT plus pwdlib over python-jose plus passlib

The current FastAPI JWT tutorial uses `PyJWT` for token handling and
`pwdlib[argon2]` for password hashing. FastAPI's docs also describe `passlib`
as the better fit for legacy-hash compatibility, not the default path for new
apps. Because the project prompt explicitly told us to verify whether
`passlib[bcrypt]` still looked like the right recommendation, we checked and
followed the current documented direction instead of forcing an older stack.

## 2026-06-29 - Tokens stored in memory only

Stage 1 keeps both access and refresh tokens in React state rather than
`localStorage`. This means a full page refresh logs the user out, but it avoids
persisting bearer tokens in a storage area that is more exposed to XSS-driven
token theft. For a portfolio project, the tradeoff is simple and easy to
explain.

## 2026-07-01 - Build Stage 2 around partial AWS readiness

AWS Cost Explorer was enabled only recently in the sandbox account, and AWS
documents that fresh Cost Explorer data can take about 24 hours to appear. We
therefore designed the sync flow to degrade gracefully: Cost Explorer
availability problems become human-readable warnings, while resource inventory
and CloudWatch metric collection can still succeed.

## 2026-07-01 - Upsert natural keys for sync idempotency

Stage 2 stores synced AWS data with database-level uniqueness constraints and
PostgreSQL upserts. That allows repeated manual sync runs without creating
duplicate cost, resource, or metric rows, which is important for demoing the
system safely and repeatedly.

## 2026-07-01 - Pivot from single-tenant AWS settings to organization-owned connections

The first Stage 2 implementation used one global AWS credential set from `.env`,
which meant all users were looking at the same dataset. To support multiple
clients safely, we introduced organizations, tenant-owned AWS connection
records, tenant-scoped sync tables, and per-organization sync execution.

## 2026-07-01 - Persist sessions across refresh at the user's request

The earlier memory-only session approach reduced XSS exposure but signed users
out on refresh. Because the product direction now prioritizes real client
usability, sessions are persisted in browser storage so users stay logged in.
This is a conscious tradeoff and should be revisited with hardened production
session handling later.

## 2026-07-01 - Resume Stage 3 only after tenant boundaries existed

The dashboard work was intentionally paused until organizations, tenant-scoped
sync tables, and org-specific AWS connections were in place. That prevents us
from building nice charts on top of the wrong data-isolation model and then
having to unwind the dashboard later.

## 2026-07-02 - Demo data must be explicit and disposable

The product needs a convincing dashboard demo path even while fresh AWS billing
data may still be unavailable. Instead of silently mixing fake and real rows,
demo data is loaded only when an admin explicitly requests it, and the next
real sync clears that seeded workspace data before persisting live AWS results.

## 2026-07-05 - Inventory coverage should follow the resources users actually test

Once users began validating the app with lightweight AWS resources like Lambda,
the earlier inventory set felt artificially narrow. The sync collector was
therefore expanded beyond EC2 and EBS to include Lambda and several other
common AWS services so the dashboard better reflects real sandbox usage.

## 2026-07-05 - Mixed resource tables must explain telemetry gaps

After broader inventory coverage landed, a shared table with EC2 CPU and
network columns made non-EC2 resources look broken because many cells read
`n/a`. The dashboard now treats that as a UX problem instead of a data problem:
it labels telemetry availability per row and reserves live CPU/network values
for the EC2 resources that actually provide them in the current sync flow.

## 2026-07-05 - Run Stage 4 findings immediately after each sync

The current app already has the freshest resource and metric data in memory at
the end of each organization sync, so that is the most reliable moment to
evaluate waste and risk rules. Running findings detection immediately after
resource and metric upserts keeps the evidence aligned with the latest sync
without introducing a second job that could drift or lag behind.

## 2026-07-05 - Use conservative first-pass thresholds for evidence-backed EC2 findings

The initial Stage 4 rules use a simple conservative banding model over the
existing EC2 CloudWatch samples: idle below 10% average CPU with low average
network traffic, underutilized from 10% up to 25%, and likely performance
mismatch at or above 85% average CPU. These thresholds are intentionally easy
to explain in a portfolio context and can be tuned later as more historical
data and richer metrics become available.
