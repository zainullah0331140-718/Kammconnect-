# KaamConnect

KaamConnect is a local services marketplace built with FastAPI, SQLAlchemy, MySQL, Jinja2, and Bootstrap. Customers can discover providers, save favorites, and submit reviews and complaints. Providers can manage business profiles, services, and advertisements. Administrators moderate verification, categories, reviews, complaints, and advertising.

## Features

- Customer, provider, and administrator accounts with Argon2 password hashing.
- Password reset for every role, with single-use hashed tokens and optional SMTP delivery.
- JWT access/refresh authentication with HttpOnly cookies and CSRF protection.
- Public provider search with category, location, rating, verification, and sorting filters.
- Provider profiles, service listings, favorites, reviews, complaints, and advertisements.
- Admin verification and moderation workflows with an audit log.
- Responsive server-rendered pages with vendored Bootstrap assets and no external CDN requirement.
- Local SVG branding assets and upload validation for profile/advertisement images.
- Pytest smoke and integration coverage using isolated SQLite test databases.

## Requirements

- Python 3.12 or newer (tested with Python 3.15).
- MySQL 8.x.
- A modern browser.

## Project Layout

```text
app/
  api/v1/routes/       API endpoints
  core/                Settings, security, templates, rate limiting
  db/                  SQLAlchemy engine, base, and types
  models/              SQLAlchemy models
  repositories/        Database queries
  schemas/             Pydantic request/response models
  services/            Business logic and serializers
  static/              CSS, JavaScript, images, vendored Bootstrap
  templates/           Jinja2 pages
  main.py              FastAPI application
  pages.py             Server-rendered page routes
database/schema.sql    Canonical MySQL schema
scripts/               Admin creation and seed commands
tests/                 Pytest suite
alembic/               Alembic environment and initial revision
```

## Setup

Run the following commands from the project root in PowerShell.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create `.env` from the example and generate a strong secret:

```powershell
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Put the generated value in `SECRET_KEY`. Replace the placeholder credentials in `DATABASE_URL` with your MySQL user and password.

Example `.env` values:

```dotenv
APP_NAME=KaamConnect
APP_ENV=development
SECRET_KEY=<generated-value>
DATABASE_URL=mysql+pymysql://kaamconnect_user:YOUR_MYSQL_PASSWORD@localhost:3306/kaamconnect_db?charset=utf8mb4
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
FRONTEND_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
UPLOAD_DIRECTORY=uploads
MAX_UPLOAD_MB=2
COOKIE_SECURE=false
REVIEWS_REQUIRE_APPROVAL=false
REVIEWS_REQUIRE_VERIFIED_PROVIDER=true
PASSWORD_RESET_EXPIRE_MINUTES=30
PASSWORD_RESET_MAX_ATTEMPTS=5
PASSWORD_RESET_WINDOW_SECONDS=900
# Optional: defaults to the first FRONTEND_ORIGINS entry.
# PASSWORD_RESET_BASE_URL=https://kaamconnect.example.com
# Optional SMTP delivery. Leave SMTP_HOST empty to disable email.
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM=no-reply@kaamconnect.local
SMTP_USE_TLS=true
SMTP_USE_SSL=false
```

For production, set `COOKIE_SECURE=true`, use HTTPS, configure SMTP, and keep `SECRET_KEY` secret.

## Database Setup

Create the database and a dedicated user in MySQL:

```sql
CREATE DATABASE kaamconnect_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER 'kaamconnect_user'@'localhost'
  IDENTIFIED BY 'replace-with-a-strong-password';

GRANT ALL PRIVILEGES ON kaamconnect_db.* TO 'kaamconnect_user'@'localhost';
FLUSH PRIVILEGES;
```

Apply the canonical schema. From Command Prompt (not PowerShell redirection syntax):

```bat
mysql -u kaamconnect_user -p kaamconnect_db < database\schema.sql
```

Then mark the initial Alembic revision as applied:

```powershell
alembic stamp head
```

Alternatively, you can run `alembic upgrade head`, but `database/schema.sql` is the canonical schema and includes MySQL-specific definitions. Do not use both methods on the same database without reviewing the resulting schema.

The models also include `refresh_tokens` and `password_reset_tokens` tables. Both store only SHA-256 token hashes, and both are part of the canonical schema.

## Seed Data and Administrator

Seed the standard categories:

```powershell
python scripts/seed_data.py
```

Optionally create clearly labelled fictional demo providers:

```powershell
python scripts/seed_data.py --demo
```

Optionally create clearly labelled fictional demo customers and reviews for existing providers:

```powershell
python scripts/seed_data.py --demo-reviews
```

Demo accounts use the password you enter. Demo profiles contain `[DEMO]`, are fictional, and remain `pending` verification. Seeded reviews use `[DEMO]` comments and include approved and pending examples. Never present them as real or verified businesses.

Create an administrator securely:

```powershell
python scripts/create_admin.py --email admin@example.com --full-name "Site Administrator"
```

The password is requested interactively and is never accepted as a command-line argument. Administrator accounts are not seeded automatically.

## Password Reset

Users of any role can recover access from `/forgot-password`:

1. Enter the account email. The API always returns a generic response so account existence is not revealed.
2. If the account exists and is active, a single-use token is stored hashed and a reset link is sent by SMTP.
3. The link opens `/reset-password?token=...`; saving a new password revokes all refresh tokens and invalidates other reset tokens.

`POST /api/v1/auth/password-reset/request`, `POST /api/v1/auth/password-reset/confirm`, and `POST /api/v1/auth/change-password` (for logged-in users) implement the flow. Administrators can also trigger a reset for a user with `POST /api/v1/admin/users/{user_id}/password-reset` or the "Reset password" button in **Admin → Manage users**.

Without SMTP configured, development and test environments return the reset link in the API response and log it; production never exposes reset tokens. Set `SMTP_HOST` (plus credentials) to deliver real email.

## Run the Application

```powershell
uvicorn app.main:app --reload
```

Open:

- Application: <http://localhost:8000>
- API documentation: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>

## Tests

Install development dependencies and run the suite:

```powershell
pip install -r requirements-dev.txt
pytest -q
```

Tests use an isolated in-memory SQLite database and dependency overrides. They do not require MySQL or a local `.env` file.

## Security Notes

- Access and refresh tokens are stored in HttpOnly cookies; the refresh cookie is scoped to `/api/v1/auth`.
- State-changing cookie-authenticated API requests require the CSRF header to match the `kc_csrf` cookie.
- Login and password-reset requests are rate-limited in-process. Multi-worker production deployments should move rate limiting to Redis or another shared store.
- Password reset tokens are single-use, time-limited, stored only as hashes, and invalidated when a new one is issued.
- Pages use a Content Security Policy with `script-src 'self'`; keep JavaScript in external files and avoid inline event handlers or inline styles.
- Uploaded images are validated before being served from `/uploads`.
- Verification badges represent platform review, not a guarantee of work quality. Users should agree on scope and pricing before work begins.

## Common Issues

- `Field required: secret_key` or `database_url`: create `.env` from `.env.example`.
- Database connection errors: confirm MySQL is running, the database exists, and `DATABASE_URL` credentials are correct.
- `Table ... doesn't exist`: apply `database/schema.sql` or run `alembic upgrade head`, then confirm `alembic stamp head` was used only with the canonical schema.
- Login redirect loops: clear cookies for `localhost` and confirm the access/refresh cookies are not being blocked.
- Image uploads fail: check `MAX_UPLOAD_MB`, the `uploads/` directory permissions, and that the image type is supported.
- Styling or scripts missing: confirm `app/static/` is present and the application is running from the project root.
