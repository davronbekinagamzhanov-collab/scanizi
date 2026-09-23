"""
ScanIZI — DataConnector base interface.
All connectors implement this interface for extensibility.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List


class DataConnector(ABC):
    """Base interface for all data connectors."""

    @abstractmethod
    def get_name(self) -> str:
        """Return connector display name."""
        ...

    @abstractmethod
    def get_type(self) -> str:
        """Return connector type: 'api', 'file', 'manual'."""
        ...

    @abstractmethod
    def get_status(self) -> str:
        """Return current status: connected, not_connected, needs_setup, error, demo."""
        ...

    @abstractmethod
    async def connect(self, config: Optional[Dict] = None) -> bool:
        """Attempt to connect / initialize."""
        ...

    @abstractmethod
    async def import_data(self, **kwargs) -> Dict[str, Any]:
        """Import data from this source. Returns import result."""
        ...

    @abstractmethod
    async def validate(self, data: Any) -> Dict[str, Any]:
        """Validate data before import."""
        ...
