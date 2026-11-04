from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import BigIntType
from app.models.enums import ComplaintStatus
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.provider import ProviderProfile
    from app.models.user import User


class Complaint(TimestampMixin, Base):
    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigIntType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider_id: Mapped[int | None] = mapped_column(
        BigIntType,
        ForeignKey("provider_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    subject: Mapped[str] = mapped_column(String(180), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=ComplaintStatus.OPEN.value, nullable=False, index=True
    )
    admin_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="complaints", foreign_keys=[user_id])
    provider: Mapped["ProviderProfile | None"] = relationship(back_populates="complaints")
