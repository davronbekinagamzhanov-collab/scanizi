"""Sales, Capital, Stores, Warehouses, Employees, Scanner, Data Sources, Demo, Recommendations APIs"""

from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File, Form
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime, timezone

from app.db.database import get_db
from app.auth.rbac import get_current_user, require_owner, require_owner_or_manager, require_any_role
from app.models.user import User, UserRole
from app.models import Product, Store, Warehouse, Category, Inventory, Sale, DataSource
from app.analytics.engine import AnalyticsEngine
from app.decision_engine.prioritizer import prioritize_products, get_attention_items, REC_TYPE_LABELS
from app.decision_engine.scorer import compute_risk_score, determine_recommendation_type
from app.ai.analyzer import analyze_product_with_ai, is_ai_available
from app.ai.portfolio_analyzer import analyze_portfolio, prepare_portfolio_metrics
from app.ai.excel_analyzer import analyze_excel_with_ai, read_file_for_analysis
from app.auth.password import hash_password
from app.schemas import SaleSummary

# ─── Sales ─────────────────────────────────────────
sales_router = APIRouter(prefix="/sales", tags=["Продажи"])


@sales_router.get("")
async def get_sales(
    days: int = Query(30, ge=1, le=365),
    store_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner_or_manager),
):
    """Get sales records with pagination."""
    from datetime import date, timedelta
    cutoff = date.today() - timedelta(days=days)

    query = (
        select(Sale, Product.name.label("product_name"), Store.name.label("store_name"))
        .join(Product, Sale.product_id == Product.id)
        .join(Store, Sale.store_id == Store.id)
        .where(Sale.sale_date >= cutoff)
    )
    if store_id:
        query = query.where(Sale.store_id == store_id)
    query = query.order_by(Sale.sale_date.desc())

    # Count
    count_q = select(func.count()).select_from(
        select(Sale.id).where(Sale.sale_date >= cutoff).subquery()
    )
    total = (await db.execute(count_q)).scalar()

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    rows = result.all()

    items = []
    for sale, product_name, store_name in rows:
        items.append({
            "id": sale.id,
            "product_id": sale.product_id,
            "product_name": product_name,
            "store_name": store_name,
            "quantity": sale.quantity,
            "unit_price": sale.unit_price,
            "total_price": sale.total_price,
            "sale_date": sale.sale_date.isoformat(),
        })

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@sales_router.get("/summary")
async def get_sales_summary(
    store_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner_or_manager),
):
    """Get sales summary with charts data."""
    engine = AnalyticsEngine(db)
    return await engine.get_sales_summary(store_id)


@sales_router.post("")
async def record_sale(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner_or_manager),
):
    """
    Record a sale transaction.
    ACID: SELECT inventory FOR UPDATE → check stock → UPDATE inventory → INSERT Sale.
    Rejects overselling. Full rollback on any error.
    """
    from sqlalchemy import text
    product_id = data.get("product_id")
    warehouse_id = data.get("warehouse_id")
    store_id = data.get("store_id")
    quantity = float(data.get("quantity", 0))
    unit_price = float(data.get("unit_price", 0))

    if not product_id or quantity <= 0:
        raise HTTPException(status_code=400, detail="product_id и quantity обязательны")

    # Validate product exists
    prod_r = await db.execute(select(Product).where(Product.id == product_id))
    product = prod_r.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    # Resolve warehouse: use provided or find first warehouse of product
    if warehouse_id:
        inv_r = await db.execute(
            select(Inventory).where(
                Inventory.product_id == product_id,
                Inventory.warehouse_id == warehouse_id,
            ).with_for_update()
        )
    else:
        inv_r = await db.execute(
            select(Inventory).where(
                Inventory.product_id == product_id,
            ).order_by(Inventory.quantity.desc()).limit(1).with_for_update()
        )

    inventory = inv_r.scalar_one_or_none()

    if not inventory:
        raise HTTPException(status_code=400, detail="Остатки для данного товара не найдены")

    if inventory.quantity < quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Недостаточно товара: доступно {inventory.quantity}, запрошено {quantity}"
        )

    # Resolve store
    if not store_id:
        wh_r = await db.execute(select(Warehouse).where(Warehouse.id == inventory.warehouse_id))
        wh = wh_r.scalar_one_or_none()
        store_id = wh.store_id if wh else None

    # UPDATE inventory (snapshot subtract)
    inventory.quantity = inventory.quantity - quantity

    # INSERT Sale (no warehouse_id on Sale model)
    from datetime import date
    sale = Sale(
        product_id=product_id,
        store_id=store_id,
        quantity=quantity,
        unit_price=unit_price or product.sale_price,
        total_price=(unit_price or product.sale_price) * quantity,
        sale_date=date.today(),
    )
    db.add(sale)
    await db.flush()

    return {
        "success": True,
        "sale_id": sale.id,
        "product": product.name,
        "quantity_sold": quantity,
        "inventory_remaining": inventory.quantity,
        "message": f"Продажа записана. Остаток: {inventory.quantity} шт.",
    }


# ─── Capital ───────────────────────────────────────
capital_router = APIRouter(prefix="/capital", tags=["Капитал"])


@capital_router.get("")
async def get_frozen_capital(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    """Get frozen capital analysis. Owner only."""
    engine = AnalyticsEngine(db)
    dashboard = await engine.compute_dashboard_metrics()
    frozen_products = await engine.get_frozen_capital_products(limit=50)

    # By category
    by_category = {}
    for p in frozen_products:
        cat = p.get("category_id", 0)
        # Get category name
        if cat:
            cat_r = await db.execute(select(Category.name).where(Category.id == cat))
            cat_name = cat_r.scalar() or "Без категории"
        else:
            cat_name = "Без категории"
        if cat_name not in by_category:
            by_category[cat_name] = 0
        by_category[cat_name] += p["inventory_value"]

    # By store
    by_store = {}
    for p in frozen_products:
        for wh in p.get("inventory_by_warehouse", []):
            store_name = wh.get("store_name", "Неизвестно")
            if store_name not in by_store:
                by_store[store_name] = 0
            by_store[store_name] += wh.get("value", 0)

    return {
        "total_capital": dashboard["total_inventory_value"],
        "frozen_capital": dashboard["frozen_capital"],
        "frozen_percent": dashboard["frozen_capital_percent"],
        "high_risk_products": [{
            "product_id": p["product_id"],
            "product_name": p["product_name"],
            "inventory_value": p["inventory_value"],
            "sales_30d": p["sales_30d"],
            "sales_90d": p["sales_90d"],
            "days_without_sale": p["days_without_sale"],
            "trend": p["trend"],
            "turnover_days": p["turnover_days"],
        } for p in frozen_products],
        "by_category": [{"category": k, "value": round(v, 2)} for k, v in sorted(by_category.items(), key=lambda x: x[1], reverse=True)],
        "by_store": [{"store": k, "value": round(v, 2)} for k, v in sorted(by_store.items(), key=lambda x: x[1], reverse=True)],
    }


# ─── Stores ────────────────────────────────────────
stores_router = APIRouter(prefix="/stores", tags=["Магазины"])


@stores_router.get("")
async def list_stores(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role),
):
    """List stores."""
    result = await db.execute(select(Store).where(Store.is_active == True))
    stores = result.scalars().all()

    items = []
    for s in stores:
        wh_count = (await db.execute(
            select(func.count(Warehouse.id)).where(Warehouse.store_id == s.id)
        )).scalar()

        items.append({
            "id": s.id,
            "name": s.name,
            "address": s.address,
            "is_active": s.is_active,
            "warehouse_count": wh_count,
        })

    return items


# ─── Warehouses ────────────────────────────────────
warehouses_router = APIRouter(prefix="/warehouses", tags=["Склады"])


@warehouses_router.get("")
async def list_warehouses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role),
):
    """List warehouses with inventory stats."""
    result = await db.execute(
        select(Warehouse, Store.name.label("store_name"))
        .join(Store, Warehouse.store_id == Store.id)
        .where(Warehouse.is_active == True)
    )
    rows = result.all()

    items = []
    for wh, store_name in rows:
        inv = await db.execute(
            select(
                func.count(Inventory.id),
                func.coalesce(func.sum(Inventory.quantity), 0),
            ).where(Inventory.warehouse_id == wh.id, Inventory.quantity > 0)
        )
        inv_row = inv.one()

        items.append({
            "id": wh.id,
            "name": wh.name,
            "store_id": wh.store_id,
            "store_name": store_name,
            "address": wh.address,
            "product_count": inv_row[0],
            "total_quantity": float(inv_row[1]),
        })

    return items


@warehouses_router.get("/transfers")
async def get_transfer_suggestions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner_or_manager),
):
    """Get suggested inventory transfers between stores."""
    engine = AnalyticsEngine(db)
    return await engine.get_transfer_suggestions()


# ─── Employees ─────────────────────────────────────
employees_router = APIRouter(prefix="/employees", tags=["Сотрудники"])


@employees_router.get("")
async def list_employees(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner_or_manager),
):
    """List employees visible to current user."""
    query = select(User, Store.name.label("store_name")).outerjoin(Store, User.store_id == Store.id)

    # Manager can only see employees of their store
    if current_user.role == UserRole.MANAGER:
        query = query.where(User.store_id == current_user.store_id)
        query = query.where(User.role != UserRole.OWNER)

    result = await db.execute(query.order_by(User.created_at.desc()))
    rows = result.all()

    return [{
        "id": u.id,
        "username": u.username,
        "full_name": u.full_name,
        "role": u.role.value if hasattr(u.role, 'value') else u.role,
        "store_id": u.store_id,
        "store_name": store_name,
        "is_active": u.is_active,
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "last_login": u.last_login.isoformat() if u.last_login else None,
    } for u, store_name in rows]


@employees_router.post("")
async def create_employee(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner_or_manager),
):
    """Create a new employee."""
    # Managers can only create employees
    role = data.get("role", "employee")
    if current_user.role == UserRole.MANAGER and role != "employee":
        raise HTTPException(status_code=403, detail="Управляющий может создавать только сотрудников")

    # Check username uniqueness
    existing = await db.execute(select(User).where(User.username == data["username"]))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Пользователь с таким логином уже существует")

    user = User(
        username=data["username"],
        password_hash=hash_password(data["password"]),
        full_name=data["full_name"],
        role=role,
        store_id=data.get("store_id"),
    )
    db.add(user)
    await db.flush()
    return {"id": user.id, "message": "Сотрудник создан"}


# ─── Scanner ───────────────────────────────────────
scanner_router = APIRouter(prefix="/scanner", tags=["Сканер"])


@scanner_router.get("/lookup")
async def scanner_lookup(
    code: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role),
):
    """Look up product by barcode or SKU."""
    result = await db.execute(
        select(Product).where(
            (Product.barcode == code) | (Product.sku == code)
        )
    )
    product = result.scalar_one_or_none()

    if not product:
        return {"found": False, "message": "Товар не найден", "product": None, "inventory": []}

    # Get inventory
    inv_result = await db.execute(
        select(Inventory, Warehouse.name.label("wh_name"), Store.name.label("store_name"))
        .join(Warehouse, Inventory.warehouse_id == Warehouse.id)
        .join(Store, Warehouse.store_id == Store.id)
        .where(Inventory.product_id == product.id)
    )
    inv_rows = inv_result.all()

    inventory = [{
        "warehouse": wh_name,
        "store": store_name,
        "quantity": inv.quantity,
    } for inv, wh_name, store_name in inv_rows]

    cat_name = None
    if product.category_id:
        cat_r = await db.execute(select(Category.name).where(Category.id == product.category_id))
        cat_name = cat_r.scalar()

    return {
        "found": True,
        "message": "Товар найден",
        "product": {
            "id": product.id,
            "name": product.name,
            "sku": product.sku,
            "barcode": product.barcode,
            "category": cat_name,
            "purchase_price": product.purchase_price,
            "sale_price": product.sale_price,
            "unit": product.unit,
        },
        "inventory": inventory,
        "total_quantity": sum(inv.quantity for inv, _, _ in inv_rows),
    }


# ─── Data Sources ──────────────────────────────────
data_router = APIRouter(prefix="/data", tags=["Данные"])


@data_router.get("/sources")
async def list_data_sources(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    """List data sources. Owner only."""
    result = await db.execute(select(DataSource).order_by(DataSource.id))
    sources = result.scalars().all()
    return [{
        "id": s.id,
        "name": s.name,
        "source_type": s.source_type,
        "status": s.status,
        "last_sync": s.last_sync.isoformat() if s.last_sync else None,
        "records_imported": s.records_imported,
    } for s in sources]


@data_router.post("/import")
async def import_file(
    file: UploadFile = File(...),
    warehouse_id: Optional[int] = Query(None),
    column_mapping: Optional[str] = Form(None),  # JSON-encoded column mapping from AI
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    """Import data from Excel or CSV file."""
    content = await file.read()
    filename = file.filename or ""

    extension = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if extension == "xlsx":
        from app.connectors.excel import ExcelConnector
        connector = ExcelConnector()
    elif extension == "csv":
        from app.connectors.excel import CSVConnector
        connector = CSVConnector()
    elif extension == "xls":
        raise HTTPException(status_code=400, detail="Формат .xls устарел и не поддерживается. Пожалуйста, сохраните файл как .xlsx или .csv.")
    else:
        raise HTTPException(status_code=400, detail="Поддерживаются только файлы Excel (.xlsx) и CSV (.csv)")

    # Validate first
    validation = await connector.validate(content)
    if not validation.get("valid"):
        return validation

    # ---------------------------------------------------------
    # Resolve destination warehouse.
    #
    # For a completely new ScanIZI installation there may be
    # zero stores/warehouses. In that case create the first
    # workspace automatically on the first real import.
    # ---------------------------------------------------------

    if warehouse_id is not None:
        wh_result = await db.execute(
            select(Warehouse, Store)
            .join(Store, Warehouse.store_id == Store.id)
            .where(
                Warehouse.id == warehouse_id,
                Warehouse.is_active == True,
            )
        )
        warehouse_row = wh_result.first()
    else:
        wh_result = await db.execute(
            select(Warehouse, Store)
            .join(Store, Warehouse.store_id == Store.id)
            .where(
                Warehouse.is_active == True,
                Store.is_active == True,
            )
            .order_by(Warehouse.id)
            .limit(1)
        )
        warehouse_row = wh_result.first()

    if warehouse_row:
        target_warehouse, target_store = warehouse_row
    else:
        # First real client import.
        store_result = await db.execute(
            select(Store)
            .where(Store.is_active == True)
            .order_by(Store.id)
            .limit(1)
        )
        target_store = store_result.scalar_one_or_none()

        if not target_store:
            target_store = Store(
                name="Мой магазин",
                address=None,
                is_active=True,
            )
            db.add(target_store)
            await db.flush()

        target_warehouse = Warehouse(
            name="Основной склад",
            store_id=target_store.id,
            address=None,
            is_active=True,
        )
        db.add(target_warehouse)
        await db.flush()

    # Owner is attached to the first workspace when it exists.
    if current_user.store_id is None:
        current_user.store_id = target_store.id

    # Parse AI-provided column mapping if supplied
    parsed_mapping = {}
    if column_mapping:
        try:
            parsed_mapping = json.loads(column_mapping)
        except (json.JSONDecodeError, TypeError):
            pass

    # Import real client data into ScanIZI database.
    result = await connector.import_data(
        file_data=content,
        warehouse_id=target_warehouse.id,
        mapping=parsed_mapping,
        db=db,
    )

    # Register/update the source.
    if result.get("success"):
        source_type = "CSV" if filename.lower().endswith(".csv") else "Excel"
        records = int(result.get("products_imported", 0)) + int(
            result.get("products_updated", 0)
        )

        source_result = await db.execute(
            select(DataSource)
            .where(DataSource.source_type == "file")
            .order_by(DataSource.id)
            .limit(1)
        )
        source = source_result.scalar_one_or_none()

        if not source:
            source = DataSource(
                name=source_type,
                source_type="file",
                status="active",
            )
            db.add(source)

        source.name = source_type
        source.status = "active"
        source.last_sync = datetime.now(timezone.utc)
        source.records_imported = records

    return result


@data_router.post("/import/preview")
async def import_preview(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    """Preview file before import."""
    content = await file.read()
    filename = file.filename or ""

    extension = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if extension == "xlsx":
        from app.connectors.excel import ExcelConnector
        connector = ExcelConnector()
    elif extension == "csv":
        from app.connectors.excel import CSVConnector
        connector = CSVConnector()
    elif extension == "xls":
        raise HTTPException(status_code=400, detail="Формат .xls устарел и не поддерживается. Пожалуйста, сохраните файл как .xlsx или .csv.")
    else:
        raise HTTPException(status_code=400, detail="Поддерживаются только файлы Excel (.xlsx) и CSV (.csv)")

    return await connector.validate(content)


@data_router.post("/ai-analyze")
async def ai_analyze_file(
    file: UploadFile = File(...),
    current_user: User = Depends(require_owner),
):
    """
    AI-powered file analysis. Reads the uploaded Excel/CSV and asks Gemini
    to intelligently map columns to the product schema + summarize the file.
    Returns the analysis without importing anything.
    """
    content = await file.read()
    filename = file.filename or ""

    if not filename.lower().endswith((".xlsx", ".xls", ".csv")):
        raise HTTPException(
            status_code=400,
            detail="Поддерживаются только .xlsx, .xls, .csv"
        )

    # Read file structure
    file_info = await read_file_for_analysis(content, filename)
    if "error" in file_info:
        return {"success": False, "error": file_info["error"]}

    # Run AI analysis
    analysis = await analyze_excel_with_ai(
        headers=file_info["headers"],
        sample_rows=file_info["sample_rows"],
        total_rows=file_info["total_rows"],
    )

    # Add preview data so frontend can show sample rows
    analysis["preview_data"] = file_info["sample_rows"][:5]
    analysis["all_headers"] = file_info["headers"]
    analysis["file_type"] = file_info["file_type"]
    analysis["success"] = True
    analysis["ai_available"] = is_ai_available()

    return analysis


# ─── Recommendations ───────────────────────────────
recommendations_router = APIRouter(prefix="/recommendations", tags=["Рекомендации"])


@recommendations_router.get("")
async def get_recommendations(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner_or_manager),
):
    """Get AI/analytics recommendations for products."""
    engine = AnalyticsEngine(db)
    all_metrics = await engine.compute_all_product_metrics()
    prioritized = prioritize_products(all_metrics)

    # Only products that need action
    actionable = [p for p in prioritized if p["rec_type"] != "NO_ACTION"][:limit]

    results = []
    for p in actionable:
        cat_name = None
        if p.get("category_id"):
            cat_r = await db.execute(select(Category.name).where(Category.id == p["category_id"]))
            cat_name = cat_r.scalar()

        results.append({
            "product_id": p["product_id"],
            "product_name": p["product_name"],
            "category": cat_name,
            "rec_type": p["rec_type"],
            "rec_type_label": p["rec_type_label"],
            "priority": p["priority"],
            "risk_score": p["risk_score"],
            "confidence": p["confidence"],
            "inventory_value": p["inventory_value"],
            "sales_30d": p["sales_30d"],
            "sales_90d": p["sales_90d"],
            "days_without_sale": p["days_without_sale"],
            "trend": p["trend"],
            "financial_impact": p.get("financial_impact", 0),
        })

    return {"items": results, "total": len(results), "ai_available": is_ai_available()}


# ─── Demo ──────────────────────────────────────────
demo_router = APIRouter(prefix="/demo", tags=["Демо"])


@demo_router.post("/load")
async def load_demo_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    """Load demo data. Owner only."""
    from app.connectors.demo import DemoDataConnector

    # Check if data already exists
    product_count = (await db.execute(select(func.count(Product.id)))).scalar()
    if product_count > 0:
        return {"success": False, "message": "Данные уже загружены. Сначала очистите базу."}

    connector = DemoDataConnector()
    result = await connector.import_data()
    return result


# ─── AI Insights ───────────────────────────────────
ai_router = APIRouter(prefix="/ai", tags=["ИИ"])


@ai_router.get("/insights")
async def get_ai_insights(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner_or_manager),
):
    """Портфельный AI-анализ бизнеса. Для владельцев и управляющих."""
    engine = AnalyticsEngine(db)
    dashboard_metrics = await engine.compute_dashboard_metrics()
    portfolio_metrics = prepare_portfolio_metrics(dashboard_metrics)
    analysis = await analyze_portfolio(portfolio_metrics)
    return {
        "analysis": analysis,
        "metrics": portfolio_metrics,
        "ai_available": is_ai_available(),
    }
