from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import BigIntType
from app.models.enums import ReviewStatus
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.provider import ProviderProfile
    from app.models.user import User


class Review(TimestampMixin, Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("provider_id", "customer_id", name="uq_reviews_provider_customer"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="rating_between_1_and_5"),
    )

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True, autoincrement=True)
    provider_id: Mapped[int] = mapped_column(
        BigIntType,
        ForeignKey("provider_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[int] = mapped_column(
        BigIntType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default=ReviewStatus.APPROVED.value, nullable=False, index=True
    )
    moderation_note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    provider: Mapped["ProviderProfile"] = relationship(back_populates="reviews")
    customer: Mapped["User"] = relationship(back_populates="reviews", foreign_keys=[customer_id])
