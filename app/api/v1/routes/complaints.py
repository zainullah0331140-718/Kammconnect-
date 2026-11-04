from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import CurrentUser
from app.models.enums import VerificationStatus
from app.models.user import User
from app.repositories.complaints import ComplaintRepository
from app.repositories.providers import ProviderRepository
from app.schemas.complaint import ComplaintCreate, ComplaintOut
from app.services.serializers import complaint_out

router = APIRouter(prefix="/complaints", tags=["Complaints"])


@router.post("", response_model=ComplaintOut, status_code=status.HTTP_201_CREATED)
def create_complaint(
    data: ComplaintCreate,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> ComplaintOut:
    provider = None
    if data.provider_id is not None:
        provider = ProviderRepository(db).get(data.provider_id)
        if (
            provider is None
            or provider.verification_status == VerificationStatus.REJECTED.value
        ):
            raise HTTPException(status_code=404, detail="Provider not found")
        if provider.user_id == user.id:
            raise HTTPException(
                status_code=400, detail="You cannot file a complaint against your own business"
            )
    complaint = ComplaintRepository(db).create(
        user_id=user.id,
        provider_id=provider.id if provider else None,
        subject=data.subject,
        message=data.message,
    )
    complaint.user = user
    complaint.provider = provider
    db.commit()
    return complaint_out(complaint)


@router.get("/me", response_model=list[ComplaintOut])
def my_complaints(
    user: CurrentUser, db: Session = Depends(get_db)
) -> list[ComplaintOut]:
    complaints = ComplaintRepository(db).list_by_user(user.id)
    return [complaint_out(complaint) for complaint in complaints]


@router.get("/{complaint_id}", response_model=ComplaintOut)
def get_complaint(
    complaint_id: int, user: CurrentUser, db: Session = Depends(get_db)
) -> ComplaintOut:
    complaint = ComplaintRepository(db).get(complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    if complaint.user_id != user.id and not user.is_admin:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint_out(complaint)
