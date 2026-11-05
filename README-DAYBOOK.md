# DAYBOOK — migration workspace

This branch introduces the new React + TypeScript frontend and modular FastAPI backend while preserving the legacy application on `main`.

## Architecture
- `frontend/`: React, TypeScript, Vite
- `backend/app/`: FastAPI application
- PostgreSQL is configured through `DATABASE_URL`; database integration and Alembic migrations are the next implementation step.

## Local development
Frontend:
```bash
cd frontend
npm install
npm run dev
```

Backend:
```bash
python -m venv .venv
# activate the environment
pip install -r backend/requirements.txt
uvicorn app.main:app --reload --app-dir backend
```

Set `VITE_API_BASE_URL` for the frontend (default: `http://localhost:8000`). Set `CORS_ORIGINS` and `DATABASE_URL` on the backend. Never commit secrets.

## Migration safety
The legacy root `index.html` and `backend/main.py` are intentionally unchanged in this branch. Do not switch production hosting to this workspace until auth, persistence, tests, and deployment configuration have been verified.
