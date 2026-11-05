from datetime import date

from sqlalchemy import Date, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    bio: Mapped[str] = mapped_column(Text, nullable=False, default="")
    birthday: Mapped[date | None] = mapped_column(Date, nullable=True)
    interests: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    theme: Mapped[str] = mapped_column(String(24), nullable=False, default="lavender")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Europe/Moscow")
