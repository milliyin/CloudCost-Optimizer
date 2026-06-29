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
