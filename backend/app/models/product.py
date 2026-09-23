"""Product model — товар"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.db.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(500), nullable=False, index=True)
    sku = Column(String(100), unique=True, nullable=False, index=True)
    barcode = Column(String(100), nullable=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    purchase_price = Column(Float, nullable=False, default=0.0)
    sale_price = Column(Float, nullable=False, default=0.0)
    description = Column(Text, nullable=True)
    unit = Column(String(50), default="шт.")
    image_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    is_seasonal = Column(Boolean, default=False)
    season_months = Column(String(100), nullable=True)  # e.g. "4,5,6,7,8" for spring-summer
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    category = relationship("Category", back_populates="products")
    inventory = relationship("Inventory", back_populates="product")
    sales = relationship("Sale", back_populates="product")
    recommendations = relationship("Recommendation", back_populates="product")
