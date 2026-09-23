"""AI Insight model — высокоуровневые инсайты для dashboard"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from datetime import datetime, timezone

from app.db.database import Base


class AIInsight(Base):
    __tablename__ = "ai_insights"

    id = Column(Integer, primary_key=True, index=True)
    insight_type = Column(String(50), nullable=False)  # frozen_capital, deficit_risk, demand_drop, etc.
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    financial_impact = Column(Float, nullable=True)
    priority = Column(Integer, default=0)  # 0-100
    data = Column(JSON, nullable=True)  # Additional structured data
    source = Column(String(20), default="analytics")  # "analytics" or "ai"
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
