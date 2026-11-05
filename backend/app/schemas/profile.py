from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


ThemeName = Literal["cloud", "blue", "lavender", "sage", "rose"]


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    bio: str | None = Field(default=None, max_length=300)
    birthday: date | None = None
    interests: list[str] | None = Field(default=None, max_length=20)
    theme: ThemeName | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=64)


class ProfileResponse(BaseModel):
    display_name: str
    email: str
    bio: str
    birthday: date | None
    interests: list[str]
    theme: ThemeName
    timezone: str
