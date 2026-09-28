# Study Bloom API

Минимальный backend для регистрации пользователей.

## Запуск локально

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

Проверка: GET /health

Регистрация: POST /register

> Пароли не хранятся в открытом виде: backend сохраняет только bcrypt-хэш.
> Для production следующим шагом нужны подтверждение email/SMS, JWT/сессии, PostgreSQL и HTTPS.
