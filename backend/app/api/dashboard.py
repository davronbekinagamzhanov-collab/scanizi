"""Dashboard API — main overview endpoint"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.auth.rbac import require_owner_or_manager
from app.models.user import User, UserRole
from app.analytics.engine import AnalyticsEngine
from app.decision_engine.prioritizer import prioritize_products, get_attention_items
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

    # 5. INSTANT ANALYTICS EXPLANATION
    # IMPORTANT:
    # Never block the main dashboard on an external AI request.
    # Gemini can be used later in a separate AI/recommendations flow.

    for item in attention:
        item["ai_analysis"] = {
            "recommendation": item["rec_type_label"],
            "reason": (
                f'Показатель критичности: {item["priority"]}/100. '
                f'Стоимость запаса: {round(item["inventory_value"], 2):,} ₽. '
                f'Продажи за 30 дней: {item["sales_30d"]} шт. '
                f'Дней без продаж: {item["days_without_sale"]} дней.'
            ),
            "evidence": {
                "key_metrics": [
                    "стоимость_запаса",
                    "продажи_30д",
                    "дней_без_продаж",
                    "тренд",
                ],
                "what_happened": item["rec_type_label"],
                "why_important": (
                    f'Показатель проблемы достигает {item["priority"]}/100.'
                ),
                "what_to_do": (
                    f'Рекомендуемое действие: {item["rec_type_label"]}.'
                ),
            },
            "confidence": item["confidence"],
            "source": "analytics",
        }

        item["ai_available"] = False

    # 6. Frozen capital items ? reuse already calculated metrics.
    frozen = await engine.get_frozen_capital_products(
        limit=10,
        all_metrics=all_metrics,
    )

    # 8. Sales and purchases summary
    sales_summary = await engine.get_sales_summary()
    sales_chart = sales_summary.get("daily_sales", [])
    purchases_summary = await engine.get_purchases_summary()

    revenue_30d = sales_summary.get("total_sales_30d", 0)
    purchase_costs_30d = purchases_summary.get("total_purchases_30d", 0)
    gross_profit_30d = revenue_30d - purchase_costs_30d

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
            "revenue_30d": revenue_30d,
            "purchase_costs_30d": purchase_costs_30d,
            "gross_profit_30d": gross_profit_30d,
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
