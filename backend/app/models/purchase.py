"""Purchase model — записи о приходах"""

from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Date, String
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.db.database import Base


class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    unit_cost = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)
    purchase_date = Column(Date, nullable=False, index=True)
    supplier = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    product = relationship("Product", back_populates="purchases")
    store = relationship("Store", back_populates="purchases")
    warehouse = relationship("Warehouse", back_populates="purchases")
