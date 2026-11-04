from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.service import ServiceOut

__all__ = [
    "AdminProviderOut",
    "LocationOut",
    "ProviderDetail",
    "ProviderOwner",
    "ProviderSearchParams",
    "ProviderSummary",
    "VerificationUpdate",
    "WorkImageOut",
]


class WorkImageOut(BaseModel):
    id: int
    image_path: str
    position: int = 0
    created_at: datetime | None = None


class ProviderSummary(BaseModel):
    id: int
    user_id: int
    business_name: str
    provider_name: str
    description: str | None = None
    experience_years: int = 0
    city: str | None = None
    area: str | None = None
    profile_image: str | None = None
    verification_status: str
    average_rating: float = 0.0
    review_count: int = 0
    services: list[ServiceOut] = Field(default_factory=list)


class ProviderDetail(ProviderSummary):
    work_images: list[WorkImageOut] = Field(default_factory=list)
    address: str | None = None
    contact_phone: str | None = None
    whatsapp_number: str | None = None
    whatsapp_link: str | None = None
    call_link: str | None = None
    is_favorite: bool = False
    created_at: datetime | None = None
    review_summary: dict = Field(default_factory=dict)


class ProviderOwner(ProviderSummary):
    work_images: list[WorkImageOut] = Field(default_factory=list)
    address: str | None = None
    contact_phone: str | None = None
    whatsapp_number: str | None = None
    verification_note: str | None = None
    verified_at: datetime | None = None
    email: str
    phone: str | None = None


class VerificationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["verified", "rejected", "pending"]
    note: str | None = Field(default=None, max_length=500)

    @field_validator("note")
    @classmethod
    def clean_note(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None


class AdminProviderOut(ProviderOwner):
    pending_reviews: int = 0
    provider_email: str = ""


class LocationOut(BaseModel):
    city: str
    areas: list[str] = Field(default_factory=list)


class ProviderSearchParams(BaseModel):
    q: str | None = None
    category: str | None = None
    city: str | None = None
    area: str | None = None
    min_rating: float = Field(default=0, ge=0, le=5)
    verified: bool | None = None
    sort: Literal["rating", "newest", "name"] = "rating"
