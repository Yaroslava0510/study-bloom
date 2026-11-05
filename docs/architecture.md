# DAYBOOK architecture decisions

## Initial architecture
Use a modular monolith: one React application, one FastAPI application, one PostgreSQL database. Keep domain modules separated; do not introduce microservices until there is a measured operational need.

## Frontend
React + TypeScript + Vite. Feature-oriented folders keep auth, study, articles, social posts, messaging and moderation independent. TanStack Query manages server state; UI state remains local unless shared across routes.

## Backend
FastAPI with API versioning under `/api/v1`, Pydantic request/response schemas, SQLAlchemy 2 repositories/services, and Alembic migrations. Keep authorization checks in backend services/dependencies, never only in the UI.

## Data
PostgreSQL is the source of truth. User-owned records must carry ownership relationships and enforce authorization on every read/write. Use UTC timestamps and store user timezone separately.

## Security
Use Argon2id password hashing, secure HttpOnly cookies, CSRF protection for cookie-authenticated mutations, rate limits for authentication and messaging, strict upload validation, and audit/moderation records. Secrets belong only in deployment environment variables.

## Migration
Keep the legacy application intact on the default branch. Build and validate the replacement on `daybook-migration`. Migrate behavior feature-by-feature; do not copy localStorage data into server records without an explicit user-approved export/import flow.
