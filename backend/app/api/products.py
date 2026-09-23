"""Products API — list, detail, create, search"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional

from app.db.database import get_db
from app.auth.rbac import require_any_role, require_owner_or_manager
from app.models.user import User
from app.models import Product, Category, Inventory, Sale, Warehouse, Store
from app.analytics.engine import AnalyticsEngine
from app.decision_engine.scorer import compute_risk_score, determine_recommendation_type, determine_confidence
from app.decision_engine.prioritizer import REC_TYPE_LABELS
from app.ai.analyzer import analyze_product_with_ai, is_ai_available
from app.schemas import ProductListItem, ProductDetail, ProductCreate, PaginatedResponse

router = APIRouter(prefix="/products", tags=["Товары"])


@router.get("")
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=200),
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    store_id: Optional[int] = None,
    risk_min: Optional[int] = None,
    sort_by: str = Query("name", regex="^(name|sale_price|purchase_price|sku)$"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role),
):
    """List products with search, filters, sorting, pagination."""
    query = select(Product).where(Product.is_active == True)

    # Search
    if search:
        query = query.where(
            or_(
                Product.name.ilike(f"%{search}%"),
                Product.sku.ilike(f"%{search}%"),
                Product.barcode.ilike(f"%{search}%"),
            )
        )

    # Category filter
    if category_id:
        query = query.where(Product.category_id == category_id)

    # Sorting
    sort_col = getattr(Product, sort_by, Product.name)
    if sort_order == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())

    # Count total
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar()

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    products = result.scalars().all()

    # Enrich with analytics
    engine = AnalyticsEngine(db)
    items = []
    for p in products:
        metrics = await engine.compute_product_metrics(p.id)
        risk = compute_risk_score(metrics)
        rec = determine_recommendation_type(metrics, risk)

        # Get category name
        cat_name = None
        if p.category_id:
            cat_r = await db.execute(select(Category.name).where(Category.id == p.category_id))
            cat_name = cat_r.scalar()

        items.append(ProductListItem(
            id=p.id,
            name=p.name,
            sku=p.sku,
            barcode=p.barcode,
            category_name=cat_name,
            purchase_price=p.purchase_price,
            sale_price=p.sale_price,
            total_quantity=metrics.get("total_quantity", 0),
            total_inventory_value=metrics.get("inventory_value", 0),
            sales_30d=metrics.get("sales_30d", 0),
            sales_90d=metrics.get("sales_90d", 0),
            last_sale_date=metrics.get("last_sale_date"),
            days_without_sale=metrics.get("days_without_sale", 0),
            trend=metrics.get("trend", "stable"),
            risk_score=risk,
            recommendation=REC_TYPE_LABELS.get(rec, rec),
        ))

    # Apply risk filter after computation
    if risk_min is not None:
        items = [i for i in items if i.risk_score >= risk_min]

    total_pages = max(1, -(-total // page_size))

    return {
        "items": [item.model_dump() for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/categories")
async def list_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role),
):
    """List all categories."""
    result = await db.execute(
        select(Category.id, Category.name, func.count(Product.id).label("count"))
        .outerjoin(Product, Product.category_id == Category.id)
        .group_by(Category.id, Category.name)
        .order_by(Category.name)
    )
    return [{"id": r[0], "name": r[1], "product_count": r[2]} for r in result.all()]


@router.get("/{product_id}")
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role),
):
    """Get detailed product view with metrics and AI analysis."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    # Compute metrics
    engine = AnalyticsEngine(db)
    metrics = await engine.compute_product_metrics(product_id)
    risk = compute_risk_score(metrics)
    rec = determine_recommendation_type(metrics, risk)
    confidence = determine_confidence(metrics, risk)

    # Category
    cat_name = None
    if product.category_id:
        cat_r = await db.execute(select(Category.name).where(Category.id == product.category_id))
        cat_name = cat_r.scalar()

    # AI Analysis
    ai_analysis = None
    enriched_metrics = {**metrics, "rec_type": rec, "rec_type_label": REC_TYPE_LABELS.get(rec, rec), "confidence": confidence}

    # Only call AI for products that need attention (not NO_ACTION)
    if rec != "NO_ACTION":
        ai_analysis = await analyze_product_with_ai(enriched_metrics)
    else:
        ai_analysis = {
            "recommendation": "Нет действий",
            "reason": "Товар находится в нормальном состоянии. Метрики не указывают на значимые проблемы.",
            "evidence": {"key_metrics": ["продажи", "остаток", "тренд"]},
            "confidence": confidence,
            "source": "analytics",
        }

    ai_analysis["ai_available"] = is_ai_available()

    return {
        "id": product.id,
        "name": product.name,
        "sku": product.sku,
        "barcode": product.barcode,
        "category_name": cat_name,
        "description": product.description,
        "unit": product.unit,
        "purchase_price": product.purchase_price,
        "sale_price": product.sale_price,
        "margin": metrics.get("margin", 0),
        "margin_percent": metrics.get("margin_percent", 0),
        "total_quantity": metrics.get("total_quantity", 0),
        "total_inventory_value": metrics.get("inventory_value", 0),
        "sales_7d": metrics.get("sales_7d", 0),
        "sales_30d": metrics.get("sales_30d", 0),
        "sales_90d": metrics.get("sales_90d", 0),
        "last_sale_date": metrics.get("last_sale_date"),
        "days_without_sale": metrics.get("days_without_sale", 0),
        "sales_velocity": metrics.get("sales_velocity", 0),
        "turnover_days": metrics.get("turnover_days", 0),
        "days_of_stock": metrics.get("days_of_stock", 0),
        "sales_change_percent": metrics.get("sales_change_percent", 0),
        "trend": metrics.get("trend", "stable"),
        "deficit_risk": metrics.get("deficit_risk", False),
        "risk_score": risk,
        "recommendation": REC_TYPE_LABELS.get(rec, rec),
        "is_seasonal": product.is_seasonal,
        "inventory_by_warehouse": metrics.get("inventory_by_warehouse", []),
        "sales_history": metrics.get("sales_history", []),
        "ai_analysis": ai_analysis,
    }


@router.post("")
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner_or_manager),
):
    """Create a new product."""
    product = Product(
        name=data.name,
        sku=data.sku,
        barcode=data.barcode,
        category_id=data.category_id,
        purchase_price=data.purchase_price,
        sale_price=data.sale_price,
        description=data.description,
        unit=data.unit,
    )
    db.add(product)
    await db.flush()
    return {"id": product.id, "message": "Товар создан"}
