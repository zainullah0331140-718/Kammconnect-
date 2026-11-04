import json
import re
from datetime import date, datetime

from app.core.security import phone_digits
from app.models.advertisement import Advertisement
from app.models.audit import AuditLog
from app.models.complaint import Complaint
from app.models.provider import ProviderProfile, ProviderService, ProviderWorkImage
from app.models.review import Review
from app.models.user import User
from app.schemas.advertisement import AdvertisementOut
from app.schemas.complaint import ComplaintOut
from app.schemas.provider import (
    ProviderDetail,
    ProviderOwner,
    ProviderSummary,
    WorkImageOut,
)
from app.schemas.review import AdminReviewOut, ReviewOut
from app.schemas.service import ServiceOut
from app.schemas.user import UserPublic


def service_out(service: ProviderService) -> ServiceOut:
    return ServiceOut(
        id=service.id,
        provider_id=service.provider_id,
        category_id=service.category_id,
        category_name=service.category.name if service.category else None,
        category_slug=service.category.slug if service.category else None,
        title=service.title,
        description=service.description,
        price_min=float(service.price_min) if service.price_min is not None else None,
        price_max=float(service.price_max) if service.price_max is not None else None,
        is_active=service.is_active,
        created_at=service.created_at,
    )


def work_image_out(image: ProviderWorkImage) -> WorkImageOut:
    return WorkImageOut(
        id=image.id,
        image_path=image.image_path,
        position=image.position,
        created_at=image.created_at,
    )


def provider_summary(
    provider: ProviderProfile, average_rating: float, review_count: int
) -> ProviderSummary:
    return ProviderSummary(
        id=provider.id,
        user_id=provider.user_id,
        business_name=provider.business_name,
        provider_name=provider.user.full_name if provider.user else "",
        description=provider.description,
        experience_years=provider.experience_years,
        city=provider.city,
        area=provider.area,
        profile_image=provider.profile_image,
        verification_status=provider.verification_status,
        average_rating=round(float(average_rating or 0), 2),
        review_count=review_count,
        services=[
            service_out(service) for service in provider.services if service.is_active
        ],
    )


def provider_detail(
    provider: ProviderProfile,
    average_rating: float,
    review_count: int,
    *,
    is_favorite: bool = False,
    review_summary: dict | None = None,
) -> ProviderDetail:
    phone = provider.contact_phone or (provider.user.phone if provider.user else None)
    digits = phone_digits(phone)
    whatsapp = provider.whatsapp_number or phone
    whatsapp_digits = phone_digits(whatsapp)
    call_link = None
    if phone:
        call_link = "tel:" + re.sub(r"[^\d+]", "", phone)
    summary = provider_summary(provider, average_rating, review_count)
    return ProviderDetail(
        **summary.model_dump(),
        work_images=[work_image_out(image) for image in provider.work_images],
        address=provider.address,
        contact_phone=phone,
        whatsapp_number=whatsapp,
        whatsapp_link=f"https://wa.me/{whatsapp_digits}" if whatsapp_digits else None,
        call_link=call_link,
        is_favorite=is_favorite,
        created_at=provider.created_at,
        review_summary=review_summary or {},
    )


def provider_owner(
    provider: ProviderProfile, average_rating: float, review_count: int
) -> ProviderOwner:
    summary = provider_summary(provider, average_rating, review_count)
    return ProviderOwner(
        **summary.model_dump(),
        work_images=[work_image_out(image) for image in provider.work_images],
        address=provider.address,
        contact_phone=provider.contact_phone,
        whatsapp_number=provider.whatsapp_number,
        verification_note=provider.verification_note,
        verified_at=provider.verified_at,
        email=provider.user.email if provider.user else "",
        phone=provider.user.phone if provider.user else None,
    )


def review_out(review: Review) -> ReviewOut:
    return ReviewOut(
        id=review.id,
        provider_id=review.provider_id,
        provider_name=review.provider.business_name if review.provider else "",
        provider_image=review.provider.profile_image if review.provider else None,
        customer_id=review.customer_id,
        customer_name=review.customer.full_name if review.customer else "",
        rating=review.rating,
        comment=review.comment,
        status=review.status,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


def admin_review_out(review: Review) -> AdminReviewOut:
    base = review_out(review)
    return AdminReviewOut(
        **base.model_dump(),
        customer_email=review.customer.email if review.customer else "",
    )


def complaint_out(complaint: Complaint) -> ComplaintOut:
    return ComplaintOut(
        id=complaint.id,
        user_id=complaint.user_id,
        user_name=complaint.user.full_name if complaint.user else "",
        user_email=complaint.user.email if complaint.user else "",
        provider_id=complaint.provider_id,
        provider_name=complaint.provider.business_name if complaint.provider else None,
        subject=complaint.subject,
        message=complaint.message,
        status=complaint.status,
        admin_response=complaint.admin_response,
        created_at=complaint.created_at,
        updated_at=complaint.updated_at,
    )


def advertisement_out(ad: Advertisement, today: date | None = None) -> AdvertisementOut:
    today = today or date.today()
    return AdvertisementOut(
        id=ad.id,
        provider_id=ad.provider_id,
        provider_name=(
            ad.provider.business_name
            if ad.provider
            else ""
        ),
        title=ad.title,
        description=ad.description,
        image_path=ad.image_path,
        destination_url=ad.destination_url,
        start_date=ad.start_date,
        end_date=ad.end_date,
        status=ad.status,
        admin_note=ad.admin_note,
        is_live=(
            ad.status == "approved" and ad.start_date <= today <= ad.end_date
        ),
        created_at=ad.created_at,
    )


def audit_out(log: AuditLog) -> dict:
    details = log.details
    if details:
        try:
            parsed = json.loads(details)
            details = json.dumps(parsed, ensure_ascii=True)
        except (TypeError, ValueError):
            pass
    return {
        "id": log.id,
        "actor_user_id": log.actor_user_id,
        "actor_name": log.actor.full_name if log.actor else None,
        "actor_email": log.actor.email if log.actor else None,
        "action": log.action,
        "entity_type": log.entity_type,
        "entity_id": log.entity_id,
        "details": details,
        "ip_address": log.ip_address,
        "created_at": log.created_at,
    }


def user_public(user: User) -> UserPublic:
    public = UserPublic.model_validate(user)
    if not public.profile_image and user.role == "provider":
        profile = user.provider_profile
        if profile is not None:
            public.profile_image = profile.profile_image
    return public


def datetime_iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
