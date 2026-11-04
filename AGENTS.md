# AGENTS.md

KaamConnect is one FastAPI app, not a monorepo. JSON API lives under `/api/v1`; public pages are Jinja2 shells whose data is loaded by JS in `app/static/js/`.

## Commands

- Use the existing venv: `.venv\Scripts\python.exe -m pytest -q` (or activate `.venv`).
- Single test: `.venv\Scripts\python.exe -m pytest tests/test_smoke.py::test_name -q`
- Dev server: `.venv\Scripts\python.exe -m uvicorn app.main:app --reload` from the repo root.
- Dev deps: `pip install -r requirements-dev.txt` (includes runtime deps).
- Seed: `python scripts/seed_data.py [--demo]`; admin: `python scripts/create_admin.py --email ... --full-name ...` (password is interactive only). Run both from the repo root.
- No lint, typecheck, formatter, pre-commit, or CI is configured. Verification is `pytest`. The suite is only 4 smoke/integration tests, not full coverage.
- Tests use the `client`, `session`, and `make_admin` fixtures. `tests/conftest.py` overrides `get_db` with a `StaticPool` in-memory SQLite engine and drops/recreates tables per test; do not use `SessionLocal` or a local MySQL DB in tests.

## Config and startup gotchas

- `app/core/config.py` instantiates settings at import time. A `.env` is required with a strong `SECRET_KEY` (>=32 chars; weak placeholder values are rejected) and `DATABASE_URL`.
- Tests set `SECRET_KEY`, `DATABASE_URL=sqlite+pysqlite:///:memory:`, etc. before importing the app in `tests/conftest.py`; they do not need MySQL or a local `.env`.
- Local `.env` currently uses MySQL (`mysql+pymysql`). The app also supports SQLite; local `kaamconnect_dev.db` and `*.log` are untracked artifacts.
- Never commit `.env`, `uploads/*`, local DB files, or logs.
- Upload directories `uploads/ads` and `uploads/profiles` are created at import/lifespan.
- API routes are included via `app/api/v1/router.py`; add new route modules there. Page routes live in `app/pages.py`; health is `/health` and `/api/v1/health`; docs at `/docs`.
- Error behavior differs by path: `/api/` returns JSON; page routes return HTML error templates. Validation errors use `{detail, errors: [{field, message, type}]}`.

## Auth and CSRF

- Auth is cookie-based (`kc_access`, `kc_refresh`) with optional Bearer tokens. Cookie-authenticated state-changing `/api/` requests need `X-CSRF-Token` matching the `kc_csrf` cookie. Exempt paths are login, both register endpoints, and `/api/v1/auth/csrf`; logout is not exempt.
- In tests use the `csrf_headers()` fixture or read `client.cookies["kc_csrf"]`.
- Browser JS should use the `KC` wrapper in `app/static/js/api.js`; it handles CSRF and the refresh-token retry. Do not hand-roll fetch calls for authenticated mutations.
- App pages use CSP `script-src 'self'`: no inline `<script>` blocks or inline event handlers. Put JavaScript in external files.

## Database, schema, and migrations

- `database/schema.sql` is the canonical MySQL 8 schema. Preferred setup: apply it, then `alembic stamp head`. Do not also run `alembic upgrade head` on the same database without reviewing the result.
- On Windows PowerShell, `<` redirection does not work; apply the schema from cmd (`mysql ... < database\schema.sql`) or pipe it with `Get-Content`.
- `database/schema.sql` already includes `refresh_tokens`; the README note suggesting it may be missing is stale.
- Alembic reads `DATABASE_URL` from `.env` via `alembic/env.py`; new models must be imported in `app/models/__init__.py` so metadata/autogenerate sees them.
- SQLite tests enable `PRAGMA foreign_keys=ON`; keep that in mind if adding cascades.

## Architecture conventions

- Flow is routes -> services -> repositories -> models/schemas. Keep SQL in `app/repositories/`, business rules in `app/services/`, serializers in `app/services/serializers.py`, and Pydantic schemas in `app/schemas/`.
- Page handlers in `app/pages.py` only render templates; page data comes from the `/api/v1` endpoints through JS. Do not add server-side data loading to pages without a clear reason.
- Roles are `customer`, `provider`, `admin`. Use `require_customer` / `require_provider` / `require_admin` and `PaginationParams` from `app/dependencies/auth.py`.
- Provider registration creates a `pending` profile; admin verification is what makes it publicly verified. Demo seed data is `[DEMO]`, fictional, and pending; never present it as real or verified.
- Login rate limiting is in-process only (`app/core/rate_limit.py`) and is not shared across workers.
