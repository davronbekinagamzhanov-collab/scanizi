"""DataSource model — источники данных (1С, GBS, Excel, CSV...)"""

from sqlalchemy import Column, Integer, String, DateTime, JSON
from datetime import datetime, timezone

from app.db.database import Base


class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # "1С", "GBS", "Excel", "CSV"
    source_type = Column(String(50), nullable=False)  # api, file, manual
    status = Column(String(50), default="not_connected")
    # Statuses: connected, not_connected, needs_setup, error, demo
    config = Column(JSON, nullable=True)
    last_sync = Column(DateTime(timezone=True), nullable=True)
    records_imported = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
