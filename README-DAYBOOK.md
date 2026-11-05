# DAYBOOK — migration workspace

This branch introduces the new React + TypeScript frontend and modular FastAPI backend while preserving the legacy application on `main`.

## Architecture
- `frontend/`: React, TypeScript, Vite
- `backend/app/`: FastAPI application and SQLAlchemy models
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
```

Apply the initial database schema:
```bash
cd backend
alembic upgrade head
```

Run the API (from the repository root):
```bash
uvicorn app.main:app --reload --app-dir backend
```

Set `VITE_API_BASE_URL` for the frontend (default: `http://localhost:8000`). Set `CORS_ORIGINS` and `DATABASE_URL` on the backend. Never commit secrets or real database credentials.

## Initial database schema
The first migration creates:
- `users`: email/contact, password hash, display name, creation time
- `password_resets`: hashed reset code/token, expiry, attempt count, one-time-use flag

The schema is a foundation only. The API does not yet use these tables for registration or password reset; those endpoints will be implemented and tested in a later migration step.

## Migration safety
The legacy root `index.html` and `backend/main.py` are intentionally unchanged in this branch. Do not switch production hosting to this workspace until authentication, persistence, tests, and deployment configuration have been verified.
