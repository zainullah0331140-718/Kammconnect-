from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ComplaintCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: int | None = None
    subject: str = Field(min_length=3, max_length=180)
    message: str = Field(min_length=10, max_length=5000)

    @field_validator("subject", "message")
    @classmethod
    def clean_text(cls, value: str) -> str:
        return value.strip()


class ComplaintUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["open", "in_review", "resolved", "rejected"]
    admin_response: str | None = Field(default=None, max_length=5000)

    @field_validator("admin_response")
    @classmethod
    def clean_response(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None


class ComplaintOut(BaseModel):
    id: int
    user_id: int
    user_name: str
    user_email: str
    provider_id: int | None = None
    provider_name: str | None = None
    subject: str
    message: str
    status: str
    admin_response: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
