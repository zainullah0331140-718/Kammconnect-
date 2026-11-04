from datetime import datetime

from pydantic import BaseModel

from app.schemas.advertisement import AdvertisementOut
from app.schemas.category import CategoryOut
from app.schemas.complaint import ComplaintOut
from app.schemas.review import AdminReviewOut


class AdminStats(BaseModel):
    total_users: int
    total_customers: int
    total_providers: int
    total_admins: int
    verified_providers: int
    pending_providers: int
    rejected_providers: int
    pending_reviews: int
    open_complaints: int
    pending_ads: int
    active_categories: int
    total_favorites: int
    recent_audit: list["AuditLogOut"] = []


class AuditLogOut(BaseModel):
    id: int
    actor_user_id: int | None = None
    actor_name: str | None = None
    actor_email: str | None = None
    action: str
    entity_type: str
    entity_id: str | None = None
    details: str | None = None
    ip_address: str | None = None
    created_at: datetime


class AdminOverview(BaseModel):
    stats: AdminStats
    pending_providers_list: list[dict] = []
    pending_reviews_list: list[AdminReviewOut] = []
    open_complaints_list: list[ComplaintOut] = []
    pending_ads_list: list[AdvertisementOut] = []
    categories: list[CategoryOut] = []


AdminStats.model_rebuild()
