import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import (
    ContentType,
    SubscriptionStatus,
    PaymentStatus,
    UserRole,
)


# ---------- USER ----------
class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: UserRole
    is_active: bool
    is_verified: bool
    avatar_url: str | None = None
    created_at: datetime


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- GENRE ----------
class GenreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str


# ---------- CONTENT ----------
class ContentBase(BaseModel):
    title: str = Field(max_length=255)
    slug: str = Field(max_length=255)
    synopsis: str | None = None
    thumbnail_url: str | None = None
    banner_url: str | None = None
    trailer_url: str | None = None
    embed_url: str | None = None
    release_year: int | None = None
    age_rating: str | None = None
    imdb_score: float | None = None
    is_featured: bool = False
    is_published: bool = False


class ContentCreate(ContentBase):
    type: ContentType
    genre_ids: list[int] = []


class ContentRead(ContentBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: ContentType
    genres: list[GenreRead] = []
    created_at: datetime


# ---------- EPISODE / SEASON ----------
class EpisodeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    episode_number: int
    title: str
    synopsis: str | None = None
    thumbnail_url: str | None = None
    embed_url: str | None = None
    duration_min: int | None = None


class SeasonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    season_number: int
    title: str | None = None
    episodes: list[EpisodeRead] = []


# ---------- PLAN / SUBSCRIPTION ----------
class PlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    price_cents: int
    currency: str
    duration_days: int
    max_devices: int
    max_quality: str


class SubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: SubscriptionStatus
    started_at: datetime
    expires_at: datetime
    auto_renew: bool
    plan: PlanRead


# ---------- FAVORITE ----------
class FavoriteCreate(BaseModel):
    content_id: uuid.UUID