from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.security import validate_phone


class ServiceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category_id: int
    title: str = Field(min_length=2, max_length=180)
    description: str | None = Field(default=None, max_length=3000)
    price_min: float | None = Field(default=None, ge=0, le=100000000)
    price_max: float | None = Field(default=None, ge=0, le=100000000)
    is_active: bool = True

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_range(self):
        if (
            self.price_min is not None
            and self.price_max is not None
            and self.price_min > self.price_max
        ):
            raise ValueError("Minimum price cannot be greater than maximum price")
        return self


class ServiceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category_id: int | None = None
    title: str | None = Field(default=None, min_length=2, max_length=180)
    description: str | None = Field(default=None, max_length=3000)
    price_min: float | None = Field(default=None, ge=0, le=100000000)
    price_max: float | None = Field(default=None, ge=0, le=100000000)
    is_active: bool | None = None

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def validate_range(self):
        if (
            self.price_min is not None
            and self.price_max is not None
            and self.price_min > self.price_max
        ):
            raise ValueError("Minimum price cannot be greater than maximum price")
        return self


class ServiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider_id: int
    category_id: int
    category_name: str | None = None
    category_slug: str | None = None
    title: str
    description: str | None = None
    price_min: float | None = None
    price_max: float | None = None
    is_active: bool
    created_at: datetime | None = None


class ProviderProfileCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_name: str = Field(min_length=2, max_length=180)
    description: str | None = Field(default=None, max_length=5000)
    experience_years: int = Field(default=0, ge=0, le=80)
    city: str = Field(min_length=2, max_length=100)
    area: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=30)
    whatsapp_number: str | None = Field(default=None, max_length=30)

    @field_validator("business_name", "city")
    @classmethod
    def clean_required(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("This field must be at least 2 characters")
        return value

    @field_validator("contact_phone", "whatsapp_number")
    @classmethod
    def clean_phone(cls, value: str | None) -> str | None:
        return validate_phone(value)


class ProviderProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_name: str | None = Field(default=None, min_length=2, max_length=180)
    description: str | None = Field(default=None, max_length=5000)
    experience_years: int | None = Field(default=None, ge=0, le=80)
    city: str | None = Field(default=None, max_length=100)
    area: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=30)
    whatsapp_number: str | None = Field(default=None, max_length=30)

    @field_validator("business_name", "city")
    @classmethod
    def clean_required(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if value and len(value) < 2:
            raise ValueError("This field must be at least 2 characters")
        return value

    @field_validator("contact_phone", "whatsapp_number")
    @classmethod
    def clean_phone(cls, value: str | None) -> str | None:
        return validate_phone(value)
