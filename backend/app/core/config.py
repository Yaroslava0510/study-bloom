from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://daybook:daybook@localhost:5432/daybook"
    cors_origins: list[str] = ["http://localhost:5173"]
    cookie_secure: bool = True
    cookie_samesite: str = "none"
    session_days: int = 14
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None


settings = Settings()
