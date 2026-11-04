from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import PaginationParams, get_client_ip, require_admin
from app.models.enums import UserRole, VerificationStatus
from app.models.user import User
from app.repositories.advertisements import AdvertisementRepository
from app.repositories.categories import CategoryRepository
from app.repositories.reviews import ReviewRepository
from app.repositories.users import UserRepository
from app.schemas.advertisement import AdminAdvertisementUpdate, AdvertisementOut
from app.schemas.admin import AdminStats, AuditLogOut
from app.schemas.auth import PasswordResetResponse
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate
from app.schemas.common import Page, paginate
from app.schemas.complaint import ComplaintOut, ComplaintUpdate
from app.schemas.provider import AdminProviderOut, VerificationUpdate
from app.schemas.review import AdminReviewOut, ReviewModeration
from app.schemas.user import AdminUserOut, AdminUserUpdate
from app.services.admin_service import AdminService
from app.services.auth_service import AuthService
from app.services.serializers import (
    admin_review_out,
    advertisement_out,
    audit_out,
    complaint_out,
)
from app.services.upload_service import delete_image_file

router = APIRouter(prefix="/admin", tags=["Administration"])


@router.get("/stats", response_model=AdminStats)
def dashboard_stats(user: User = Depends(require_admin), db: Session = Depends(get_db)) -> AdminStats:
    return AdminService(db).stats()


@router.get("/users", response_model=Page[AdminUserOut])
def list_users(
    pagination: PaginationParams,
    role: Literal["customer", "provider", "admin"] | None = None,
    q: str | None = Query(None, max_length=120),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    items, total = AdminService(db).list_users(
        role=role, q=q, page=pagination.page, page_size=pagination.page_size
    )
    return paginate(items, total, pagination.page, pagination.page_size)


@router.patch("/users/{user_id}", response_model=AdminUserOut)
def update_user(
    user_id: int,
    data: AdminUserUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    service = AdminService(db)
    result = service.update_user(
        admin=admin,
        user_id=user_id,
        data=data,
        ip_address=get_client_ip(request),
    )
    db.commit()
    return result


@router.post("/users/{user_id}/password-reset", response_model=PasswordResetResponse)
def send_user_password_reset(
    user_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    target = UserRepository(db).get(user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    payload = AuthService(db).admin_password_reset(
        target=target, admin=admin, ip_address=get_client_ip(request)
    )
    db.commit()
    return payload


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    image_paths = AdminService(db).delete_user(
        admin=admin,
        user_id=user_id,
        ip_address=get_client_ip(request),
    )
    db.commit()
    for image_path in image_paths:
        delete_image_file(image_path)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/providers", response_model=Page[AdminProviderOut])
def list_verification_providers(
    pagination: PaginationParams,
    status_filter: Literal["pending", "verified", "rejected"] | None = Query(
        None, alias="status"
    ),
    q: str | None = Query(None, max_length=120),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    items, total = AdminService(db).list_verification_providers(
        status_filter=status_filter,
        q=q,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return paginate(items, total, pagination.page, pagination.page_size)


@router.patch("/providers/{provider_id}/verification", response_model=AdminProviderOut)
def set_provider_verification(
    provider_id: int,
    data: VerificationUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    service = AdminService(db)
    result = service.set_verification(
        admin=admin,
        provider_id=provider_id,
        data=data,
        ip_address=get_client_ip(request),
    )
    db.commit()
    return result


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(
    user: User = Depends(require_admin), db: Session = Depends(get_db)
) -> list[dict]:
    return AdminService(db).list_categories()


@router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(
    data: CategoryCreate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    service = AdminService(db)
    category = service.create_category(
        admin=admin, data=data, ip_address=get_client_ip(request)
    )
    db.commit()
    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "description": category.description,
        "icon": category.icon,
        "is_active": category.is_active,
        "provider_count": 0,
    }


@router.patch("/categories/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int,
    data: CategoryUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    service = AdminService(db)
    category = service.update_category(
        admin=admin,
        category_id=category_id,
        data=data,
        ip_address=get_client_ip(request),
    )
    db.commit()
    counts = CategoryRepository(db).provider_counts()
    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "description": category.description,
        "icon": category.icon,
        "is_active": category.is_active,
        "provider_count": counts.get(category.id, 0),
    }


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    service = AdminService(db)
    service.delete_category(
        admin=admin, category_id=category_id, ip_address=get_client_ip(request)
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/reviews", response_model=Page[AdminReviewOut])
def list_reviews(
    pagination: PaginationParams,
    status_filter: Literal["pending", "approved", "rejected"] | None = Query(
        None, alias="status"
    ),
    q: str | None = Query(None, max_length=200),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    items, total = AdminService(db).list_reviews(
        status_filter=status_filter,
        q=q,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return paginate(items, total, pagination.page, pagination.page_size)


@router.patch("/reviews/{review_id}", response_model=AdminReviewOut)
def moderate_review(
    review_id: int,
    data: ReviewModeration,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    service = AdminService(db)
    review = service.moderate_review(
        admin=admin,
        review_id=review_id,
        new_status=data.status,
        note=data.note,
        ip_address=get_client_ip(request),
    )
    db.commit()
    review = ReviewRepository(db).get(review.id)
    return admin_review_out(review).model_dump()


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(
    review_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    service = AdminService(db)
    service.delete_review(
        admin=admin, review_id=review_id, ip_address=get_client_ip(request)
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/complaints", response_model=Page[ComplaintOut])
def list_complaints(
    pagination: PaginationParams,
    status_filter: Literal["open", "in_review", "resolved", "rejected"] | None = Query(
        None, alias="status"
    ),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    items, total = AdminService(db).list_complaints(
        status_filter=status_filter,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return paginate(items, total, pagination.page, pagination.page_size)


@router.patch("/complaints/{complaint_id}", response_model=ComplaintOut)
def update_complaint(
    complaint_id: int,
    data: ComplaintUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    service = AdminService(db)
    complaint = service.update_complaint(
        admin=admin,
        complaint_id=complaint_id,
        new_status=data.status,
        admin_response=data.admin_response,
        ip_address=get_client_ip(request),
    )
    db.commit()
    complaint = service.complaints.get(complaint.id)
    return complaint_out(complaint).model_dump()


@router.get("/advertisements", response_model=Page[AdvertisementOut])
def list_advertisements(
    pagination: PaginationParams,
    status_filter: Literal["pending", "approved", "rejected", "expired"] | None = Query(
        None, alias="status"
    ),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    items, total = AdminService(db).list_ads(
        status_filter=status_filter,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return paginate(items, total, pagination.page, pagination.page_size)


@router.patch("/advertisements/{ad_id}", response_model=AdvertisementOut)
def moderate_advertisement(
    ad_id: int,
    data: AdminAdvertisementUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    service = AdminService(db)
    ad = service.moderate_ad(
        admin=admin,
        ad_id=ad_id,
        new_status=data.status,
        note=data.note,
        ip_address=get_client_ip(request),
    )
    db.commit()
    ad = AdvertisementRepository(db).get(ad.id)
    return advertisement_out(ad).model_dump()


@router.get("/audit-logs", response_model=Page[AuditLogOut])
def list_audit_logs(
    pagination: PaginationParams,
    action: str | None = Query(None, max_length=100),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    items, total = AdminService(db).list_audit(
        action=action, page=pagination.page, page_size=pagination.page_size
    )
    return paginate(items, total, pagination.page, pagination.page_size)
