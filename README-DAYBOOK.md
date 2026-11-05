# DAYBOOK — migration workspace

This branch introduces the new React + TypeScript frontend and modular FastAPI backend while preserving the legacy application on `main`.

## Architecture
- `frontend/`: React, TypeScript, Vite
- `backend/app/`: FastAPI application, authentication routes and SQLAlchemy models
- PostgreSQL is the intended source of truth.
- Alembic manages schema changes.

## Local development

Frontend:
```bash
cd frontend
npm install
npm run dev
```

Backend (from the repository root):
```bash
python -m venv .venv
# activate the environment
pip install -r backend/requirements.txt
```

Configure the backend environment before running migrations:
```bash
export DATABASE_URL='postgresql+asyncpg://USER:PASSWORD@HOST:5432/DATABASE'
export COOKIE_SECURE=false
export COOKIE_SAMESITE=lax
export RESET_CODE_PEPPER='GENERATE_A_LONG_RANDOM_SECRET_AND_KEEP_IT_PRIVATE'
```

Apply the database schema and run the API:
```bash
cd backend
alembic upgrade head
cd ..
uvicorn app.main:app --reload --app-dir backend
```

Set `VITE_API_BASE_URL` for the frontend (default: `http://localhost:8000`). Set `CORS_ORIGINS` and `DATABASE_URL` on the backend. For password-reset email, configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` and optionally `SMTP_FROM`. `RESET_CODE_PEPPER` is required for password-reset codes; use a long random secret and keep it private. For `CORS_ORIGINS`, provide a JSON array of exact trusted origins, for example `[\"https://your-site.example\"]`. Never commit secrets or real database credentials.

## Authentication API

All routes use the `/api/v1/auth` prefix:
- `GET /csrf`: issues a CSRF token cookie and returns the token for the request header
- `POST /register`: creates an account and starts a server-side session
- `POST /login`: verifies credentials and starts a server-side session
- `POST /logout`: revokes the current session
- `GET /me`: returns the authenticated account
- `POST /password-reset/request`: sends a six-digit email code
- `POST /password-reset/verify`: verifies the code and returns a short-lived reset token
- `POST /password-reset/complete`: changes the password and revokes existing sessions

Passwords are hashed with Argon2. Session tokens are stored only as hashes in PostgreSQL and are delivered in HttpOnly cookies. Reset codes expire after 10 minutes and allow at most five attempts. Password-reset requests are rate-limited per email and client IP using atomic, database-backed 15-minute buckets (3 requests per email / 10 per IP); code verification has separate limits (10 per email / 30 per IP). Old rate-limit buckets are pruned during requests.

## Database migrations
- `0001_initial_auth`: users and password reset records
- `0002_user_sessions`: server-side login sessions
- `0003_rate_limit_buckets`: persistent rate-limit counters for password-reset endpoints

## Important verification status
The routes and schema have been added to this migration branch. The frontend registration, login and password-reset screens are wired to the API helpers. GitHub Actions now runs the backend test suite with SQLite and applies Alembic migrations to a temporary PostgreSQL 16 service; the frontend also runs a production build. Check the Actions page for the latest run status. This CI PostgreSQL service is temporary and is not a production database. SMTP delivery, browser-level end-to-end flows, and the production hosting/cookie configuration still require separate verification.

## Migration safety
The legacy root `index.html` and `backend/main.py` on `main` are intentionally unchanged. Do not switch production hosting to this workspace until authentication, persistence, tests, rate limiting, and deployment configuration have been verified.
