from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AdvertisementOut(BaseModel):
    id: int
    provider_id: int
    provider_name: str
    title: str
    description: str
    image_path: str
    destination_url: str
    start_date: date
    end_date: date
    status: str
    admin_note: str | None = None
    is_live: bool = False
    created_at: datetime


class AdminAdvertisementUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["approved", "rejected", "pending", "expired"]
    note: str | None = Field(default=None, max_length=500)
