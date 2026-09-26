"""Для чего нужен этот файл:
Описывает таблицы базы данных и их поля. ORM преобразует эти модели Python в записи базы данных и обратно.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    area: Mapped[float] = mapped_column(Float, nullable=False)
    rooms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    floor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    address: Mapped[str] = mapped_column(String(512), nullable=False)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False, default="apartment")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    photos: Mapped[list["Photo"]] = relationship(
        "Photo", back_populates="listing", cascade="all, delete-orphan"
    )


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    listing_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("listings.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    is_main: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    listing: Mapped["Listing"] = relationship("Listing", back_populates="photos")
