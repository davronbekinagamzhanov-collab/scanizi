"""Pydantic schemas for API request/response validation"""

from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime, date
from enum import Enum


# ─── Auth ───────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    store_id: Optional[int] = None
    store_name: Optional[str] = None
    is_active: bool

    model_config = {"from_attributes": True}


# ─── Store / Warehouse ─────────────────────────────
class StoreResponse(BaseModel):
    id: int
    name: str
    address: Optional[str] = None
    is_active: bool
    warehouse_count: int = 0
    product_count: int = 0
    total_inventory_value: float = 0.0

    model_config = {"from_attributes": True}


class WarehouseResponse(BaseModel):
    id: int
    name: str
    store_id: int
    store_name: str = ""
    address: Optional[str] = None
    is_active: bool
    product_count: int = 0
    total_quantity: float = 0.0
    total_value: float = 0.0

    model_config = {"from_attributes": True}


# ─── Category ──────────────────────────────────────
class CategoryResponse(BaseModel):
    id: int
    name: str
    product_count: int = 0

    model_config = {"from_attributes": True}


# ─── Product ───────────────────────────────────────
class ProductListItem(BaseModel):
    id: int
    name: str
    sku: str
    barcode: Optional[str] = None
    category_name: Optional[str] = None
    purchase_price: float
    sale_price: float
    total_quantity: float = 0.0
    total_inventory_value: float = 0.0
    sales_30d: int = 0
    sales_90d: int = 0
    last_sale_date: Optional[date] = None
    days_without_sale: int = 0
    trend: str = "stable"
    risk_score: int = 0
    recommendation: Optional[str] = None

    model_config = {"from_attributes": True}


class ProductDetail(ProductListItem):
    description: Optional[str] = None
    unit: str = "шт."
    margin: float = 0.0
    margin_percent: float = 0.0
    sales_7d: int = 0
    sales_velocity: float = 0.0
    turnover_days: float = 0.0
    days_of_stock: float = 0.0
    stock_change_percent: float = 0.0
    is_seasonal: bool = False
    inventory_by_warehouse: List[dict] = []
    sales_history: List[dict] = []
    ai_analysis: Optional[dict] = None

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    name: str
    sku: str
    barcode: Optional[str] = None
    category_id: Optional[int] = None
    purchase_price: float
    sale_price: float
    description: Optional[str] = None
    unit: str = "шт."


# ─── Sales ──────────────────────────────────────────
class SaleSummary(BaseModel):
    total_sales_today: float = 0.0
    total_sales_7d: float = 0.0
    total_sales_30d: float = 0.0
    total_sales_90d: float = 0.0
    sales_count_today: int = 0
    sales_count_30d: int = 0
    top_products: List[dict] = []
    declining_products: List[dict] = []
    sales_by_category: List[dict] = []
    daily_sales: List[dict] = []


class SaleRecord(BaseModel):
    id: int
    product_id: int
    product_name: str
    store_name: str
    quantity: float
    unit_price: float
    total_price: float
    sale_date: date

    model_config = {"from_attributes": True}


# ─── Dashboard ──────────────────────────────────────
class DashboardMetrics(BaseModel):
    total_inventory_value: float = 0.0
    frozen_capital: float = 0.0
    frozen_capital_percent: float = 0.0
    products_at_risk: int = 0
    potential_deficit: int = 0
    avg_stock_age_days: float = 0.0
    sales_30d: float = 0.0
    turnover_days: float = 0.0
    total_products: int = 0
    total_stores: int = 0
    total_warehouses: int = 0


class DashboardResponse(BaseModel):
    metrics: DashboardMetrics
    attention_items: List[dict] = []
    frozen_capital_items: List[dict] = []
    sales_chart: List[dict] = []


# ─── Capital ────────────────────────────────────────
class CapitalResponse(BaseModel):
    total_capital: float = 0.0
    frozen_capital: float = 0.0
    frozen_percent: float = 0.0
    high_risk_products: List[dict] = []
    by_category: List[dict] = []
    by_store: List[dict] = []


# ─── Recommendation ────────────────────────────────
class RecommendationResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    store_name: Optional[str] = None
    rec_type: str
    priority: int
    confidence: str
    financial_impact: Optional[float] = None
    recommendation_text: str
    reason: str
    evidence: Optional[dict] = None
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Employee ──────────────────────────────────────
class EmployeeCreate(BaseModel):
    username: str
    password: str
    full_name: str
    role: str = "employee"
    store_id: Optional[int] = None


class EmployeeResponse(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    store_id: Optional[int] = None
    store_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── Data Source ───────────────────────────────────
class DataSourceResponse(BaseModel):
    id: int
    name: str
    source_type: str
    status: str
    last_sync: Optional[datetime] = None
    records_imported: int = 0

    model_config = {"from_attributes": True}


# ─── Import ───────────────────────────────────────
class ImportPreview(BaseModel):
    columns_detected: List[str] = []
    column_mapping: dict = {}
    total_rows: int = 0
    valid_rows: int = 0
    error_rows: int = 0
    errors: List[dict] = []
    preview_data: List[dict] = []


class ImportResult(BaseModel):
    success: bool
    products_imported: int = 0
    products_updated: int = 0
    errors: List[dict] = []
    message: str = ""


# ─── Scanner ──────────────────────────────────────
class ScannerResult(BaseModel):
    found: bool
    product: Optional[ProductListItem] = None
    inventory: List[dict] = []
    message: str = ""


# ─── Warehouse Transfer ──────────────────────────
class TransferSuggestion(BaseModel):
    product_id: int
    product_name: str
    from_store: str
    from_warehouse: str
    from_quantity: float
    to_store: str
    to_warehouse: str
    to_quantity: float
    suggested_transfer: float
    reason: str


# ─── Pagination ──────────────────────────────────
class PaginatedResponse(BaseModel):
    items: List[Any] = []
    total: int = 0
    page: int = 1
    page_size: int = 50
    total_pages: int = 0
