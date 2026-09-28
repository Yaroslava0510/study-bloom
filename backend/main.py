from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from passlib.context import CryptContext
import sqlite3

app = FastAPI(title="Study Bloom API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yaroslava0510.github.io"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
DB = "study_bloom.db"

def init_db():
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contact TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        name TEXT NOT NULL
    )""")
    con.commit()
    con.close()

init_db()

class Register(BaseModel):
    contact: str
    password: str
    name: str

@app.get("/health")
def health():
    return {"ok": True, "service": "study-bloom-api"}

@app.post("/register")
def register(data: Register):
    if len(data.password) < 8:
        raise HTTPException(400, "Пароль должен содержать минимум 8 символов")
    con = sqlite3.connect(DB)
    try:
        cur = con.execute(
            "INSERT INTO users(contact,password_hash,name) VALUES(?,?,?)",
            (data.contact.strip().lower(), pwd.hash(data.password), data.name.strip())
        )
        con.commit()
        return {"id": cur.lastrowid, "name": data.name.strip()}
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Этот email или телефон уже зарегистрирован")
    finally:
        con.close()
