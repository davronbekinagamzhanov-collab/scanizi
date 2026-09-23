"""Sale model — записи о продажах"""

from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Date
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.db.database import Base


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    sale_date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    product = relationship("Product", back_populates="sales")
    store = relationship("Store", back_populates="sales")
