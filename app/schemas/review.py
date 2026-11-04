from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReviewCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: int
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)

    @field_validator("comment")
    @classmethod
    def clean_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ReviewUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)

    @field_validator("comment")
    @classmethod
    def clean_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ReviewOut(BaseModel):
    id: int
    provider_id: int
    provider_name: str
    provider_image: str | None = None
    customer_id: int
    customer_name: str
    rating: int
    comment: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime | None = None


class AdminReviewOut(ReviewOut):
    customer_email: str


class ReviewModeration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["approved", "rejected", "pending"]
    note: str | None = Field(default=None, max_length=500)


class RatingSummary(BaseModel):
    average_rating: float
    review_count: int
    pending_count: int = 0
    distribution: dict[int, int] = Field(default_factory=dict)
