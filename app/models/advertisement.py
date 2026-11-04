from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import BigIntType
from app.models.enums import AdvertisementStatus
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.provider import ProviderProfile


class Advertisement(TimestampMixin, Base):
    __tablename__ = "advertisements"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True, autoincrement=True)
    provider_id: Mapped[int] = mapped_column(
        BigIntType,
        ForeignKey("provider_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    image_path: Mapped[str] = mapped_column(String(255), nullable=False)
    destination_url: Mapped[str] = mapped_column(String(500), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20), default=AdvertisementStatus.PENDING.value, nullable=False, index=True
    )
    admin_note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    provider: Mapped["ProviderProfile"] = relationship(back_populates="advertisements")
