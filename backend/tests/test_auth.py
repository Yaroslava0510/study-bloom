import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api import auth
from app.db import Base, get_db
from app.main import app


@pytest_asyncio.fixture
async def client(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(auth.settings, "cookie_secure", False)
    monkeypatch.setattr(auth.settings, "cookie_samesite", "lax")
    monkeypatch.setattr(auth.settings, "reset_code_pepper", "test-only-reset-pepper")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client

    app.dependency_overrides.clear()
    await engine.dispose()


async def csrf_headers(client):
    response = await client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    return {"X-CSRF-Token": response.json()["csrf_token"]}


@pytest.mark.asyncio
async def test_register_login_me_and_logout(client):
    headers = await csrf_headers(client)
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "Student@example.com", "password": "safe-password-123", "name": "Student"},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["email"] == "student@example.com"
    assert "daybook_session" in client.cookies

    me_response = await client.get("/api/v1/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["name"] == "Student"

    bad_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "student@example.com", "password": "incorrect-password"},
        headers=await csrf_headers(client),
    )
    assert bad_login.status_code == 401

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "STUDENT@example.com", "password": "safe-password-123"},
        headers=await csrf_headers(client),
    )
    assert login.status_code == 200

    logout = await client.post("/api/v1/auth/logout", headers=await csrf_headers(client))
    assert logout.status_code == 204
    assert (await client.get("/api/v1/auth/me")).status_code == 401


@pytest.mark.asyncio
async def test_password_reset_changes_password_and_revokes_sessions(client, monkeypatch):
    sent_codes = []
    monkeypatch.setattr(auth, "send_reset_email", lambda email, code: sent_codes.append((email, code)))

    register = await client.post(
        "/api/v1/auth/register",
        json={"email": "reset@example.com", "password": "old-password-123", "name": "Reset"},
        headers=await csrf_headers(client),
    )
    assert register.status_code == 201

    request = await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "RESET@example.com"},
    )
    assert request.status_code == 200
    assert request.json() == {"ok": True}
    assert len(sent_codes) == 1
    assert sent_codes[0][0] == "reset@example.com"

    verify = await client.post(
        "/api/v1/auth/password-reset/verify",
        json={"email": "reset@example.com", "code": sent_codes[0][1]},
    )
    assert verify.status_code == 200
    reset_token = verify.json()["token"]

    complete = await client.post(
        "/api/v1/auth/password-reset/complete",
        json={
            "email": "reset@example.com",
            "token": reset_token,
            "password": "new-password-456",
        },
    )
    assert complete.status_code == 200
    assert complete.json() == {"ok": True}
    assert (await client.get("/api/v1/auth/me")).status_code == 401

    old_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "reset@example.com", "password": "old-password-123"},
        headers=await csrf_headers(client),
    )
    assert old_login.status_code == 401

    new_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "reset@example.com", "password": "new-password-456"},
        headers=await csrf_headers(client),
    )
    assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_password_reset_rejects_wrong_code_and_unknown_email(client, monkeypatch):
    sent_codes = []
    monkeypatch.setattr(auth, "send_reset_email", lambda email, code: sent_codes.append(code))

    await client.post(
        "/api/v1/auth/register",
        json={"email": "wrong-code@example.com", "password": "safe-password-123", "name": ""},
        headers=await csrf_headers(client),
    )
    unknown = await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "nobody@example.com"},
    )
    assert unknown.status_code == 200
    assert unknown.json() == {"ok": True}
    assert sent_codes == []

    await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "wrong-code@example.com"},
    )
    wrong = await client.post(
        "/api/v1/auth/password-reset/verify",
        json={"email": "wrong-code@example.com", "code": "000000" if sent_codes[0] != "000000" else "000001"},
    )
    assert wrong.status_code == 400



@pytest.mark.asyncio
async def test_password_reset_request_is_rate_limited_per_email(client):
    for _ in range(3):
        response = await client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": "unknown-rate-limit@example.com"},
        )
        assert response.status_code == 200

    limited = await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "unknown-rate-limit@example.com"},
    )
    assert limited.status_code == 429
    assert limited.headers["Retry-After"] == "900"


@pytest.mark.asyncio
async def test_password_reset_code_locks_after_five_wrong_attempts(client, monkeypatch):
    sent_codes = []
    monkeypatch.setattr(auth, "send_reset_email", lambda email, code: sent_codes.append(code))
    await client.post(
        "/api/v1/auth/register",
        json={"email": "attempts@example.com", "password": "safe-password-123", "name": "Attempts"},
        headers=await csrf_headers(client),
    )
    await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "attempts@example.com"},
    )

    wrong_code = "000000" if sent_codes[0] != "000000" else "000001"
    for _ in range(5):
        response = await client.post(
            "/api/v1/auth/password-reset/verify",
            json={"email": "attempts@example.com", "code": wrong_code},
        )
        assert response.status_code == 400

    locked = await client.post(
        "/api/v1/auth/password-reset/verify",
        json={"email": "attempts@example.com", "code": sent_codes[0]},
    )
    assert locked.status_code == 400
