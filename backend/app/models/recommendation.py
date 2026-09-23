"""Recommendation model — AI/Analytics рекомендации по товарам"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.db.database import Base


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True)

    # Recommendation type: RESTOCK, OBSERVE, CONSIDER_DISCOUNT, CONSIDER_RETURN,
    # CONSIDER_TRANSFER, DO_NOT_PURCHASE, NO_ACTION
    rec_type = Column(String(50), nullable=False)
    priority = Column(Integer, default=0)  # 0-100, higher = more urgent
    confidence = Column(String(20), default="medium")  # low, medium, high
    financial_impact = Column(Float, nullable=True)

    # Explanation
    recommendation_text = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    evidence = Column(JSON, nullable=True)

    # Source
    source = Column(String(20), default="analytics")  # "analytics" or "ai"

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    product = relationship("Product", back_populates="recommendations")
