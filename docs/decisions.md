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
