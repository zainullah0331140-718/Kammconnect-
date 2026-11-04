from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import BigIntType
from app.models.enums import VerificationStatus
from app.models.mixins import TimestampMixin, utcnow

if TYPE_CHECKING:
    from app.models.advertisement import Advertisement
    from app.models.category import ServiceCategory
    from app.models.complaint import Complaint
    from app.models.favorite import Favorite
    from app.models.review import Review
    from app.models.user import User


class ProviderProfile(TimestampMixin, Base):
    __tablename__ = "provider_profiles"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigIntType, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    business_name: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    experience_years: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    area: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    whatsapp_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    profile_image: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verification_status: Mapped[str] = mapped_column(
        String(20), default=VerificationStatus.PENDING.value, nullable=False, index=True
    )
    verification_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship(back_populates="provider_profile")
    services: Mapped[list["ProviderService"]] = relationship(
        back_populates="provider", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="provider", cascade="all, delete-orphan"
    )
    favorites: Mapped[list["Favorite"]] = relationship(
        back_populates="provider", cascade="all, delete-orphan"
    )
    complaints: Mapped[list["Complaint"]] = relationship(
        back_populates="provider", cascade="all, delete-orphan"
    )
    advertisements: Mapped[list["Advertisement"]] = relationship(
        back_populates="provider", cascade="all, delete-orphan"
    )
    work_images: Mapped[list["ProviderWorkImage"]] = relationship(
        back_populates="provider",
        cascade="all, delete-orphan",
        order_by="ProviderWorkImage.position",
    )

    @property
    def is_verified(self) -> bool:
        return self.verification_status == VerificationStatus.VERIFIED.value


class ProviderService(TimestampMixin, Base):
    __tablename__ = "provider_services"
    __table_args__ = (
        CheckConstraint("price_min IS NULL OR price_min >= 0", name="price_min_non_negative"),
        CheckConstraint("price_max IS NULL OR price_max >= 0", name="price_max_non_negative"),
        CheckConstraint(
            "price_min IS NULL OR price_max IS NULL OR price_min <= price_max",
            name="price_range_valid",
        ),
    )

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True, autoincrement=True)
    provider_id: Mapped[int] = mapped_column(
        BigIntType,
        ForeignKey("provider_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[int] = mapped_column(
        BigIntType,
        ForeignKey("service_categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_min: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    price_max: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    provider: Mapped["ProviderProfile"] = relationship(back_populates="services")
    category: Mapped["ServiceCategory"] = relationship(back_populates="services")


class ProviderWorkImage(TimestampMixin, Base):
    __tablename__ = "provider_work_images"
    __table_args__ = (
        CheckConstraint("position >= 0", name="position_non_negative"),
    )

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True, autoincrement=True)
    provider_id: Mapped[int] = mapped_column(
        BigIntType,
        ForeignKey("provider_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    image_path: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    provider: Mapped["ProviderProfile"] = relationship(back_populates="work_images")
