"""
1С Connector — stub with honest status.
No fake integration. Will be implemented when real 1С API is available.
"""

from typing import Optional, Dict, Any
from app.connectors.base import DataConnector


class OneCConnector(DataConnector):
    def get_name(self) -> str:
        return "1С"

    def get_type(self) -> str:
        return "api"

    def get_status(self) -> str:
        return "not_connected"

    async def connect(self, config: Optional[Dict] = None) -> bool:
        return False

    async def import_data(self, **kwargs) -> Dict[str, Any]:
        return {"success": False, "message": "1С интеграция пока не подключена. Требуется настройка."}

    async def validate(self, data: Any) -> Dict[str, Any]:
        return {"valid": False, "message": "1С интеграция пока не подключена."}
