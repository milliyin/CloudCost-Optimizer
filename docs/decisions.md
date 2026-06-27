# Decision Notes

## 2026-06-27 - Vite chosen for frontend scaffolding

Vite is the current recommended React scaffolding path for a lightweight client
app, and it keeps Stage 0 fast to understand and demo.

## 2026-06-27 - PostgreSQL provisioned from day one

The project prompt expects relational data with migrations and auditability.
Provisioning Postgres in Stage 0 keeps the local stack aligned with the later
stages instead of swapping databases midstream.
