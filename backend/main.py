from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
import hashlib
import os
import secrets
import smtplib
import sqlite3
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

app = FastAPI(title="Study Bloom API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yaroslava0510.github.io"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
DB = os.getenv("DB_PATH", "study_bloom.db")
RESET_MINUTES = 10
MAX_CODE_ATTEMPTS = 5


def now_utc():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.isoformat()


def hash_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def init_db():
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contact TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        name TEXT NOT NULL
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS password_resets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        code_hash TEXT NOT NULL,
        token_hash TEXT,
        expires_at TEXT NOT NULL,
        attempts INTEGER NOT NULL DEFAULT 0,
        used INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")
    con.commit()
    con.close()


init_db()


class Register(BaseModel):
    contact: EmailStr
    password: str
    name: str = ""


class ResetRequest(BaseModel):
    contact: EmailStr


class ResetVerify(BaseModel):
    contact: EmailStr
    code: str


class ResetComplete(BaseModel):
    contact: EmailStr
    token: str
    password: str


@app.get("/")
def root():
    return {"ok": True, "service": "study-bloom-api"}


@app.get("/health")
def health():
    return {"ok": True, "service": "study-bloom-api"}


@app.post("/register")
def register(data: Register):
    if len(data.password) < 8:
        raise HTTPException(400, "Пароль должен содержать минимум 8 символов")
    contact = str(data.contact).strip().lower()
    name = data.name.strip()
    con = sqlite3.connect(DB)
    try:
        cur = con.execute(
            "INSERT INTO users(contact,password_hash,name) VALUES(?,?,?)",
            (contact, pwd.hash(data.password), name)
        )
        con.commit()
        return {"id": cur.lastrowid, "name": name}
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Этот email уже зарегистрирован")
    finally:
        con.close()


def send_reset_email(to_email: str, code: str):
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM") or user

    if not all([host, user, password, sender]):
        raise RuntimeError("SMTP is not configured on the server")

    msg = EmailMessage()
    msg["Subject"] = "Код восстановления Study Bloom"
    msg["From"] = sender
    msg["To"] = to_email
    msg.set_content(
        f"""Привет!

Твой код восстановления Study Bloom:

{code}

Код действует {RESET_MINUTES} минут и одноразовый.

Если ты не запрашивала восстановление пароля, просто проигнорируй это письмо.

Study Bloom ✦
"""
    )

    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=20) as smtp:
            smtp.login(user, password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(user, password)
            smtp.send_message(msg)


@app.post("/password-reset/request")
def password_reset_request(data: ResetRequest):
    contact = str(data.contact).strip().lower()
    con = sqlite3.connect(DB)
    try:
        user = con.execute(
            "SELECT id FROM users WHERE contact=?",
            (contact,)
        ).fetchone()

        if not user:
            return {"ok": True}

        con.execute(
            "UPDATE password_resets SET used=1 WHERE user_id=? AND used=0",
            (user[0],)
        )

        code = f"{secrets.randbelow(1000000):06d}"
        expires = now_utc() + timedelta(minutes=RESET_MINUTES)
        con.execute(
            """INSERT INTO password_resets
               (user_id,code_hash,expires_at,attempts,used)
               VALUES(?,?,?,?,0)""",
            (user[0], hash_value(code), iso(expires), 0)
        )
        con.commit()

        try:
            send_reset_email(contact, code)
        except Exception:
            con.execute(
                "UPDATE password_resets SET used=1 WHERE user_id=? AND used=0",
                (user[0],)
            )
            con.commit()
            raise HTTPException(
                503,
                "Не удалось отправить письмо. Проверь настройки почты сервера."
            )

        return {"ok": True}
    finally:
        con.close()


@app.post("/password-reset/verify")
def password_reset_verify(data: ResetVerify):
    contact = str(data.contact).strip().lower()
    code = data.code.strip()

    if not code.isdigit() or len(code) != 6:
        raise HTTPException(400, "Код должен состоять из 6 цифр")

    con = sqlite3.connect(DB)
    try:
        row = con.execute(
            """SELECT pr.id, pr.code_hash, pr.expires_at, pr.attempts
               FROM password_resets pr
               JOIN users u ON u.id=pr.user_id
               WHERE u.contact=? AND pr.used=0
               ORDER BY pr.id DESC LIMIT 1""",
            (contact,)
        ).fetchone()

        if not row:
            raise HTTPException(400, "Код недействителен или срок его действия истёк")

        reset_id, code_hash, expires_at, attempts = row

        if datetime.fromisoformat(expires_at) < now_utc():
            con.execute("UPDATE password_resets SET used=1 WHERE id=?", (reset_id,))
            con.commit()
            raise HTTPException(400, "Код недействителен или срок его действия истёк")

        if attempts >= MAX_CODE_ATTEMPTS:
            con.execute("UPDATE password_resets SET used=1 WHERE id=?", (reset_id,))
            con.commit()
            raise HTTPException(429, "Слишком много попыток. Запроси новый код.")

        if not secrets.compare_digest(hash_value(code), code_hash):
            con.execute(
                "UPDATE password_resets SET attempts=attempts+1 WHERE id=?",
                (reset_id,)
            )
            con.commit()
            raise HTTPException(400, "Неверный код")

        token = secrets.token_urlsafe(32)
        con.execute(
            "UPDATE password_resets SET token_hash=? WHERE id=?",
            (hash_value(token), reset_id)
        )
        con.commit()
        return {"ok": True, "token": token}
    finally:
        con.close()


@app.post("/password-reset/complete")
def password_reset_complete(data: ResetComplete):
    if len(data.password) < 8:
        raise HTTPException(400, "Новый пароль должен содержать минимум 8 символов")

    contact = str(data.contact).strip().lower()
    con = sqlite3.connect(DB)
    try:
        row = con.execute(
            """SELECT pr.id, pr.user_id, pr.token_hash, pr.expires_at
               FROM password_resets pr
               JOIN users u ON u.id=pr.user_id
               WHERE u.contact=? AND pr.used=0
               ORDER BY pr.id DESC LIMIT 1""",
            (contact,)
        ).fetchone()

        if not row or not row[2]:
            raise HTTPException(400, "Сначала подтверди код из письма")

        reset_id, user_id, token_hash, expires_at = row

        if datetime.fromisoformat(expires_at) < now_utc():
            con.execute("UPDATE password_resets SET used=1 WHERE id=?", (reset_id,))
            con.commit()
            raise HTTPException(400, "Срок восстановления истёк. Запроси новый код.")

        if not secrets.compare_digest(hash_value(data.token), token_hash):
            raise HTTPException(400, "Восстановление недействительно")

        con.execute(
            "UPDATE users SET password_hash=? WHERE id=?",
            (pwd.hash(data.password), user_id)
        )
        con.execute("UPDATE password_resets SET used=1 WHERE id=?", (reset_id,))
        con.commit()
        return {"ok": True}
    finally:
        con.close()
