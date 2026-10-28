from datetime import datetime
from typing import Optional
from sqlalchemy import (
    BigInteger,
    String,
    Boolean,
    Text,
    Integer,
    Float,
    JSON,
    ForeignKey,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[Optional[str]] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Subscription(Base):
    __tablename__ = "subscriptions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    city: Mapped[str] = mapped_column(String)
    max_price: Mapped[Optional[int]] = mapped_column(Integer)
    min_rooms: Mapped[Optional[int]] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")
    no_agencies: Mapped[bool] = mapped_column(Boolean, server_default="true")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Listing(Base):
    __tablename__ = "listings"
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    url: Mapped[str] = mapped_column(String(512))
    price: Mapped[int] = mapped_column(Integer)
    address: Mapped[str] = mapped_column(Text)
    rooms: Mapped[Optional[int]] = mapped_column(Integer)
    prob_agency: Mapped[Optional[float]] = mapped_column(Float)
    prob_fake: Mapped[Optional[float]] = mapped_column(Float)
    extracted_entities: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )


class MLDataset(Base):
    __tablename__ = "ml_dataset"
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    seller_id: Mapped[Optional[str]] = mapped_column(String(255))
    avito_url: Mapped[str] = mapped_column(String(512))
    images_path: Mapped[Optional[dict]] = mapped_column(JSON)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    duplicate_of_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    text_description: Mapped[str] = mapped_column(Text)
    price: Mapped[int] = mapped_column(Integer)
    rooms: Mapped[Optional[int]] = mapped_column(Integer)
    is_ai_generated: Mapped[Optional[bool]] = mapped_column(
        Boolean, server_default="false"
    )
    label_is_agency: Mapped[bool] = mapped_column(Boolean)
    label_is_fake: Mapped[bool] = mapped_column(Boolean)
    label_hidden_fees: Mapped[Optional[bool]] = mapped_column(Boolean)
    total_area: Mapped[Optional[float]] = mapped_column(Float)
    floor: Mapped[Optional[int]] = mapped_column(Integer)
    total_floors: Mapped[Optional[int]] = mapped_column(Integer)
    deposit: Mapped[Optional[int]] = mapped_column(Integer)
    renovation: Mapped[Optional[str]] = mapped_column(String(50))
    address: Mapped[Optional[str]] = mapped_column(String(512))
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    images: Mapped[list["ApartmentImage"]] = relationship(
        back_populates="apartment", cascade="all, delete-orphan"
    )


class ApartmentImage(Base):
    __tablename__ = "apartment_images"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    apartment_id: Mapped[str] = mapped_column(
        ForeignKey("ml_dataset.id", ondelete="CASCADE")
    )
    image_path: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    embedding = mapped_column(Vector(2048))
    apartment: Mapped["MLDataset"] = relationship(back_populates="images")
