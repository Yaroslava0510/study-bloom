from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user, require_csrf
from app.db import get_db
from app.models.profile import UserProfile
from app.models.user import User
from app.schemas.profile import ProfileResponse, ProfileUpdate

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


async def get_or_create_profile(user: User, db: AsyncSession) -> UserProfile:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = UserProfile(user_id=user.id)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile


def to_response(user: User, profile: UserProfile) -> ProfileResponse:
    return ProfileResponse(
        display_name=user.name,
        email=user.contact,
        bio=profile.bio,
        birthday=profile.birthday,
        interests=profile.interests or [],
        theme=profile.theme,
        timezone=profile.timezone,
    )


@router.get("/me", response_model=ProfileResponse)
async def read_my_profile(
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await get_or_create_profile(user, db)
    return to_response(user, profile)


@router.patch("/me", response_model=ProfileResponse)
async def update_my_profile(
    data: ProfileUpdate,
    request: Request,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    require_csrf(request)
    updates = data.model_dump(exclude_unset=True)
    if "display_name" in updates:
        display_name = updates.pop("display_name")
        if display_name is not None:
            user.name = display_name.strip()
            if not user.name:
                raise HTTPException(status_code=422, detail="Имя не может быть пустым")
    if "interests" in updates and updates["interests"] is not None:
        cleaned = []
        for interest in updates["interests"]:
            value = interest.strip()
            if value and value not in cleaned:
                cleaned.append(value)
        updates["interests"] = cleaned

    profile = await get_or_create_profile(user, db)
    for field, value in updates.items():
        setattr(profile, field, value)
    await db.commit()
    await db.refresh(profile)
    await db.refresh(user)
    return to_response(user, profile)
