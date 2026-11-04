import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

ICON_RE = re.compile(r"^[a-z0-9-]{1,60}$")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug[:120]


class CategoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=100)
    slug: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    icon: str | None = Field(default=None, max_length=80)
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("slug")
    @classmethod
    def clean_slug(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        slug = slugify(value)
        if not slug:
            raise ValueError("Enter a valid slug")
        return slug

    @field_validator("icon")
    @classmethod
    def clean_icon(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        value = value.strip()
        if not ICON_RE.match(value):
            raise ValueError("Icon must contain only lowercase letters, numbers, and hyphens")
        return value


class CategoryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=100)
    slug: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    icon: str | None = Field(default=None, max_length=80)
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("slug")
    @classmethod
    def clean_slug(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        slug = slugify(value)
        if not slug:
            raise ValueError("Enter a valid slug")
        return slug

    @field_validator("icon")
    @classmethod
    def clean_icon(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        value = value.strip()
        if not ICON_RE.match(value):
            raise ValueError("Icon must contain only lowercase letters, numbers, and hyphens")
        return value


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str | None = None
    icon: str | None = None
    is_active: bool
    provider_count: int = 0
