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
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB


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
    avito_url: Mapped[str] = mapped_column(String(512))
    images_path: Mapped[Optional[dict]] = mapped_column(JSON)
    text_description: Mapped[str] = mapped_column(Text)
    price: Mapped[int] = mapped_column(Integer)
    rooms: Mapped[Optional[int]] = mapped_column(Integer)
    label_is_agency: Mapped[bool] = mapped_column(Boolean)  # True - "Agency"
    label_is_fake: Mapped[bool] = mapped_column(Boolean)  # True - "Fake"
    label_hidden_fees: Mapped[Optional[bool]] = mapped_column(Boolean)
    total_area: Mapped[Optional[float]] = mapped_column(Float)
    floor: Mapped[Optional[int]] = mapped_column(Integer)
    total_floors: Mapped[Optional[int]] = mapped_column(Integer)
    deposit: Mapped[Optional[int]] = mapped_column(Integer)
    renovation: Mapped[Optional[str]] = mapped_column(String(50))
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
