"""Dashboard API — main overview endpoint"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.auth.rbac import require_owner_or_manager
from app.models.user import User, UserRole
from app.analytics.engine import AnalyticsEngine
from app.decision_engine.prioritizer import prioritize_products, get_attention_items
from app.ai.analyzer import analyze_batch_with_ai, is_ai_available
from app.schemas import DashboardResponse

router = APIRouter(tags=["Обзор"])


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner_or_manager),
):
    """Get dashboard overview with real metrics, AI insights, and frozen capital."""
    engine = AnalyticsEngine(db)

    # 1. Compute all product metrics ONCE and reuse them.
    all_metrics = await engine.compute_all_product_metrics()

    # 2. Compute dashboard metrics from the already calculated metrics.
    dashboard_metrics = await engine.compute_dashboard_metrics(all_metrics)

    # 3. Prioritize (Decision Engine)
    prioritized = prioritize_products(all_metrics)

    # 4. Get attention items
    attention = get_attention_items(prioritized, limit=5)

    # 5. AI Analysis for top items
    if attention:
        ai_results = await analyze_batch_with_ai(attention)
        for i, item in enumerate(attention):
            for ai_r in ai_results:
                if ai_r.get("product_id") == item["product_id"]:
                    item["ai_analysis"] = ai_r
                    break

    # 6. AI availability flag
    for item in attention:
        item["ai_available"] = is_ai_available()

    # 7. Frozen capital items ? reuse already calculated metrics.
    frozen = await engine.get_frozen_capital_products(
        limit=10,
        all_metrics=all_metrics,
    )

    # 8. Sales chart (30 days)
    sales_summary = await engine.get_sales_summary()
    sales_chart = sales_summary.get("daily_sales", [])

    # Store counts
    from sqlalchemy import select, func
    from app.models import Store, Warehouse
    stores_count = (await db.execute(select(func.count(Store.id)))).scalar()
    wh_count = (await db.execute(select(func.count(Warehouse.id)))).scalar()

    return DashboardResponse(
        metrics={
            **dashboard_metrics,
            "total_stores": stores_count,
            "total_warehouses": wh_count,
        },
        attention_items=attention,
        frozen_capital_items=[{
            "product_id": f["product_id"],
            "product_name": f["product_name"],
            "inventory_value": f["inventory_value"],
            "sales_30d": f["sales_30d"],
            "sales_90d": f["sales_90d"],
            "days_without_sale": f["days_without_sale"],
            "trend": f["trend"],
            "turnover_days": f["turnover_days"],
        } for f in frozen],
        sales_chart=sales_chart,
    )
