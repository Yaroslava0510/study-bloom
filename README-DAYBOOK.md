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
```

Apply the database schema and run the API:
```bash
cd backend
alembic upgrade head
cd ..
uvicorn app.main:app --reload --app-dir backend
```

Set `VITE_API_BASE_URL` for the frontend (default: `http://localhost:8000`). Set `CORS_ORIGINS` and `DATABASE_URL` on the backend. For password-reset email, configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` and optionally `SMTP_FROM`. Never commit secrets or real database credentials.

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

Passwords are hashed with Argon2. Session tokens are stored only as hashes in PostgreSQL and are delivered in HttpOnly cookies. Reset codes expire after 10 minutes and allow at most five attempts.

## Database migrations
- `0001_initial_auth`: users and password reset records
- `0002_user_sessions`: server-side login sessions

## Important verification status
The routes and schema have been added to this migration branch, but no live PostgreSQL database has been connected and no migration, backend startup, email delivery, or end-to-end authentication test has yet been run. Add request rate limiting and automated tests before any public deployment. The current frontend still needs registration, login and password-reset screens wired to these API helpers.

## Migration safety
The legacy root `index.html` and `backend/main.py` on `main` are intentionally unchanged. Do not switch production hosting to this workspace until authentication, persistence, tests, rate limiting, and deployment configuration have been verified.
