"""
ScanIZI Analytics Engine — чистая математика, Python/Pandas/NumPy.
Отвечает на вопрос: «Что произошло?»
AI не считает арифметику — все числа приходят отсюда.
"""

import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta, timezone
from typing import List, Dict, Optional, Any
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Product, Sale, Inventory, Warehouse, Store, Category


class AnalyticsEngine:
    """Core analytics engine — computes all metrics from raw DB data."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.today = date.today()

    async def compute_product_metrics(self, product_id: int) -> Dict[str, Any]:
        """Compute all metrics for a single product."""
        # Fetch product
        result = await self.db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
        if not product:
            return {}

        # Fetch inventory across all warehouses
        inv_result = await self.db.execute(
            select(Inventory, Warehouse, Store)
            .join(Warehouse, Inventory.warehouse_id == Warehouse.id)
            .join(Store, Warehouse.store_id == Store.id)
            .where(Inventory.product_id == product_id)
        )
        inventory_rows = inv_result.all()

        total_quantity = sum(row[0].quantity for row in inventory_rows)
        inventory_value = total_quantity * product.purchase_price
        potential_revenue = total_quantity * product.sale_price

        # Inventory by warehouse
        inventory_by_warehouse = []
        for inv, wh, st in inventory_rows:
            inventory_by_warehouse.append({
                "warehouse_id": wh.id,
                "warehouse_name": wh.name,
                "store_id": st.id,
                "store_name": st.name,
                "quantity": inv.quantity,
                "value": inv.quantity * product.purchase_price,
            })

        # Sales data
        sales_7d = await self._get_sales_count(product_id, 7)
        sales_30d = await self._get_sales_count(product_id, 30)
        sales_90d = await self._get_sales_count(product_id, 90)
        sales_365d = await self._get_sales_count(product_id, 365)

        # Sales revenue
        revenue_30d = await self._get_sales_revenue(product_id, 30)
        revenue_90d = await self._get_sales_revenue(product_id, 90)

        # Last sale date
        last_sale = await self._get_last_sale_date(product_id)
        days_without_sale = (self.today - last_sale).days if last_sale else 999

        # Sales velocity (units per day over 30 days)
        sales_velocity = sales_30d / 30.0 if sales_30d > 0 else 0.0

        # Average daily sales (90-day basis)
        avg_daily_sales = sales_90d / 90.0 if sales_90d > 0 else 0.0

        # Days of stock coverage
        days_of_stock = (total_quantity / avg_daily_sales) if avg_daily_sales > 0 else 9999.0

        # Turnover (days to sell entire stock based on 30d rate)
        turnover_days = (total_quantity / (sales_30d / 30.0)) if sales_30d > 0 else 9999.0

        # Margin
        margin = product.sale_price - product.purchase_price
        margin_percent = (margin / product.purchase_price * 100) if product.purchase_price > 0 else 0.0

        # Trend: compare last 30d vs previous 30d
        sales_prev_30d = await self._get_sales_count_range(
            product_id, 60, 30
        )
        if sales_prev_30d > 0:
            sales_change = ((sales_30d - sales_prev_30d) / sales_prev_30d) * 100
        elif sales_30d > 0:
            sales_change = 100.0
        else:
            sales_change = 0.0

        # Determine trend
        if sales_change > 15:
            trend = "growing"
        elif sales_change < -15:
            trend = "declining"
        else:
            trend = "stable"

        # Predicted stock in 30 days
        predicted_stock_30d = max(0, total_quantity - (avg_daily_sales * 30))

        # Deficit risk
        deficit_risk = False
        if avg_daily_sales > 0 and days_of_stock < 14:
            deficit_risk = True

        # Sales history (daily, last 90 days)
        sales_history = await self._get_daily_sales_history(product_id, 90)

        # Seasonality
        is_seasonal = product.is_seasonal
        season_months = []
        if product.season_months:
            season_months = [int(m) for m in product.season_months.split(",")]

        return {
            "product_id": product_id,
            "product_name": product.name,
            "sku": product.sku,
            "barcode": product.barcode,
            "category_id": product.category_id,
            "purchase_price": product.purchase_price,
            "sale_price": product.sale_price,
            "margin": round(margin, 2),
            "margin_percent": round(margin_percent, 1),
            "total_quantity": total_quantity,
            "inventory_value": round(inventory_value, 2),
            "potential_revenue": round(potential_revenue, 2),
            "sales_7d": sales_7d,
            "sales_30d": sales_30d,
            "sales_90d": sales_90d,
            "sales_365d": sales_365d,
            "revenue_30d": round(revenue_30d, 2),
            "revenue_90d": round(revenue_90d, 2),
            "last_sale_date": last_sale.isoformat() if last_sale else None,
            "days_without_sale": days_without_sale,
            "sales_velocity": round(sales_velocity, 3),
            "avg_daily_sales": round(avg_daily_sales, 3),
            "days_of_stock": round(min(days_of_stock, 9999), 1),
            "turnover_days": round(min(turnover_days, 9999), 1),
            "sales_change_percent": round(sales_change, 1),
            "trend": trend,
            "predicted_stock_30d": round(predicted_stock_30d, 1),
            "deficit_risk": deficit_risk,
            "is_seasonal": is_seasonal,
            "season_months": season_months,
            "current_month": self.today.month,
            "inventory_by_warehouse": inventory_by_warehouse,
            "sales_history": sales_history,
        }

    async def compute_all_product_metrics(self) -> List[Dict[str, Any]]:
        """Compute metrics for all active products."""
        result = await self.db.execute(
            select(Product.id).where(Product.is_active == True)
        )
        product_ids = [row[0] for row in result.all()]
        metrics = []
        for pid in product_ids:
            m = await self.compute_product_metrics(pid)
            if m:
                metrics.append(m)
        return metrics

    async def compute_dashboard_metrics(self) -> Dict[str, Any]:
        """Compute high-level dashboard metrics."""
        all_metrics = await self.compute_all_product_metrics()

        if not all_metrics:
            return {
                "total_inventory_value": 0,
                "frozen_capital": 0,
                "frozen_capital_percent": 0,
                "products_at_risk": 0,
                "potential_deficit": 0,
                "avg_stock_age_days": 0,
                "sales_30d": 0,
                "turnover_days": 0,
                "total_products": 0,
            }

        total_value = sum(m["inventory_value"] for m in all_metrics)

        # Frozen capital: products with turnover > 90 days and value > 0
        frozen = sum(
            m["inventory_value"]
            for m in all_metrics
            if m["turnover_days"] > 90 and m["inventory_value"] > 0
            and not (m["is_seasonal"] and m["current_month"] not in m.get("season_months", []))
        )

        frozen_percent = (frozen / total_value * 100) if total_value > 0 else 0

        # Products at risk: high turnover days + significant value
        at_risk = sum(
            1 for m in all_metrics
            if m["turnover_days"] > 120 and m["inventory_value"] > 5000
        )

        # Potential deficit
        deficit = sum(1 for m in all_metrics if m["deficit_risk"])

        # Average stock age (simplified: days since last sale, weighted by value)
        total_weighted_age = sum(
            m["days_without_sale"] * m["inventory_value"]
            for m in all_metrics if m["inventory_value"] > 0
        )
        avg_age = total_weighted_age / total_value if total_value > 0 else 0

        # Total sales 30d
        total_sales_30d = sum(m["revenue_30d"] for m in all_metrics)

        # Average turnover
        valuable = [m for m in all_metrics if m["inventory_value"] > 0 and m["turnover_days"] < 9999]
        avg_turnover = np.mean([m["turnover_days"] for m in valuable]) if valuable else 0

        return {
            "total_inventory_value": round(total_value, 2),
            "frozen_capital": round(frozen, 2),
            "frozen_capital_percent": round(frozen_percent, 1),
            "products_at_risk": at_risk,
            "potential_deficit": deficit,
            "avg_stock_age_days": round(avg_age, 1),
            "sales_30d": round(total_sales_30d, 2),
            "turnover_days": round(avg_turnover, 1),
            "total_products": len(all_metrics),
        }

    async def get_frozen_capital_products(self, limit: int = 50) -> List[Dict]:
        """Get products where money is frozen (slow-moving + high value)."""
        all_metrics = await self.compute_all_product_metrics()

        frozen = [
            m for m in all_metrics
            if m["turnover_days"] > 60 and m["inventory_value"] > 1000
        ]
        frozen.sort(key=lambda x: x["inventory_value"], reverse=True)
        return frozen[:limit]

    async def get_sales_summary(self, store_id: Optional[int] = None) -> Dict:
        """Compute sales summary for dashboard."""
        conditions = []
        if store_id:
            conditions.append(Sale.store_id == store_id)

        # Daily sales for last 30 days
        daily_sales = []
        for i in range(30):
            d = self.today - timedelta(days=i)
            q = select(func.coalesce(func.sum(Sale.total_price), 0)).where(
                Sale.sale_date == d
            )
            if conditions:
                q = q.where(*conditions)
            result = await self.db.execute(q)
            total = result.scalar()
            daily_sales.append({"date": d.isoformat(), "total": round(float(total), 2)})

        daily_sales.reverse()

        # Top products by revenue 30d
        thirty_ago = self.today - timedelta(days=30)
        top_q = (
            select(
                Product.id, Product.name,
                func.sum(Sale.quantity).label("qty"),
                func.sum(Sale.total_price).label("revenue")
            )
            .join(Product, Sale.product_id == Product.id)
            .where(Sale.sale_date >= thirty_ago)
        )
        if conditions:
            top_q = top_q.where(*conditions)
        top_q = top_q.group_by(Product.id, Product.name).order_by(
            func.sum(Sale.total_price).desc()
        ).limit(10)
        top_result = await self.db.execute(top_q)
        top_products = [
            {"product_id": r[0], "name": r[1], "quantity": float(r[2]), "revenue": round(float(r[3]), 2)}
            for r in top_result.all()
        ]

        # Sales by category
        cat_q = (
            select(
                Category.name,
                func.sum(Sale.total_price).label("revenue")
            )
            .join(Product, Sale.product_id == Product.id)
            .join(Category, Product.category_id == Category.id)
            .where(Sale.sale_date >= thirty_ago)
        )
        if conditions:
            cat_q = cat_q.where(*conditions)
        cat_q = cat_q.group_by(Category.name).order_by(func.sum(Sale.total_price).desc())
        cat_result = await self.db.execute(cat_q)
        sales_by_category = [
            {"category": r[0], "revenue": round(float(r[1]), 2)}
            for r in cat_result.all()
        ]

        # Revenue totals
        today_rev = await self._get_total_revenue(0, store_id)
        rev_7d = await self._get_total_revenue(7, store_id)
        rev_30d = await self._get_total_revenue(30, store_id)
        rev_90d = await self._get_total_revenue(90, store_id)

        return {
            "total_sales_today": today_rev,
            "total_sales_7d": rev_7d,
            "total_sales_30d": rev_30d,
            "total_sales_90d": rev_90d,
            "top_products": top_products,
            "sales_by_category": sales_by_category,
            "daily_sales": daily_sales,
        }

    async def get_transfer_suggestions(self) -> List[Dict]:
        """Find products with imbalanced inventory across stores."""
        # Get all products with inventory in multiple warehouses
        result = await self.db.execute(
            select(
                Inventory.product_id,
                func.count(Inventory.warehouse_id)
            )
            .where(Inventory.quantity > 0)
            .group_by(Inventory.product_id)
            .having(func.count(Inventory.warehouse_id) > 1)
        )
        multi_wh = result.all()

        suggestions = []
        for product_id, _ in multi_wh:
            metrics = await self.compute_product_metrics(product_id)
            if not metrics or len(metrics["inventory_by_warehouse"]) < 2:
                continue

            # Check for imbalance: one store has excess, another has deficit
            wh_data = metrics["inventory_by_warehouse"]

            # Get sales by store
            store_sales = {}
            for wh in wh_data:
                sid = wh["store_id"]
                if sid not in store_sales:
                    sales_count = await self._get_sales_count_by_store(product_id, sid, 30)
                    store_sales[sid] = {
                        "store_name": wh["store_name"],
                        "sales_30d": sales_count,
                        "total_qty": 0,
                        "warehouse_name": wh["warehouse_name"],
                    }
                store_sales[sid]["total_qty"] += wh["quantity"]

            stores = list(store_sales.values())
            if len(stores) < 2:
                continue

            # Sort by sales velocity (sales / quantity ratio)
            for s in stores:
                s["velocity"] = s["sales_30d"] / max(s["total_qty"], 1)

            stores.sort(key=lambda x: x["velocity"])
            low_vel = stores[0]  # excess stock, low sales
            high_vel = stores[-1]  # low stock, high sales

            # Significant imbalance check
            if (low_vel["total_qty"] > high_vel["total_qty"] * 3
                    and high_vel["sales_30d"] > low_vel["sales_30d"] * 1.5):
                suggested = min(
                    low_vel["total_qty"] * 0.3,
                    high_vel["sales_30d"] * 2
                )
                if suggested >= 1:
                    suggestions.append({
                        "product_id": product_id,
                        "product_name": metrics["product_name"],
                        "from_store": low_vel["store_name"],
                        "from_warehouse": low_vel["warehouse_name"],
                        "from_quantity": low_vel["total_qty"],
                        "to_store": high_vel["store_name"],
                        "to_warehouse": high_vel["warehouse_name"],
                        "to_quantity": high_vel["total_qty"],
                        "suggested_transfer": round(suggested),
                        "reason": (
                            f'В магазине «{low_vel["store_name"]}» сформирован избыточный остаток '
                            f'({int(low_vel["total_qty"])} шт.), а в магазине «{high_vel["store_name"]}» '
                            f'наблюдается более высокая скорость продаж. '
                            f'Рассмотрите перемещение части запаса.'
                        ),
                    })

        suggestions.sort(key=lambda x: x["suggested_transfer"], reverse=True)
        return suggestions[:20]

    # ─── Helper queries ───────────────────────────────

    async def _get_sales_count(self, product_id: int, days: int) -> int:
        cutoff = self.today - timedelta(days=days)
        result = await self.db.execute(
            select(func.coalesce(func.sum(Sale.quantity), 0))
            .where(Sale.product_id == product_id, Sale.sale_date >= cutoff)
        )
        return int(result.scalar())

    async def _get_sales_count_range(self, product_id: int, days_from: int, days_to: int) -> int:
        start = self.today - timedelta(days=days_from)
        end = self.today - timedelta(days=days_to)
        result = await self.db.execute(
            select(func.coalesce(func.sum(Sale.quantity), 0))
            .where(
                Sale.product_id == product_id,
                Sale.sale_date >= start,
                Sale.sale_date < end
            )
        )
        return int(result.scalar())

    async def _get_sales_count_by_store(self, product_id: int, store_id: int, days: int) -> int:
        cutoff = self.today - timedelta(days=days)
        result = await self.db.execute(
            select(func.coalesce(func.sum(Sale.quantity), 0))
            .where(
                Sale.product_id == product_id,
                Sale.store_id == store_id,
                Sale.sale_date >= cutoff
            )
        )
        return int(result.scalar())

    async def _get_sales_revenue(self, product_id: int, days: int) -> float:
        cutoff = self.today - timedelta(days=days)
        result = await self.db.execute(
            select(func.coalesce(func.sum(Sale.total_price), 0.0))
            .where(Sale.product_id == product_id, Sale.sale_date >= cutoff)
        )
        return float(result.scalar())

    async def _get_last_sale_date(self, product_id: int) -> Optional[date]:
        result = await self.db.execute(
            select(func.max(Sale.sale_date))
            .where(Sale.product_id == product_id)
        )
        return result.scalar()

    async def _get_daily_sales_history(self, product_id: int, days: int) -> List[Dict]:
        cutoff = self.today - timedelta(days=days)
        result = await self.db.execute(
            select(Sale.sale_date, func.sum(Sale.quantity), func.sum(Sale.total_price))
            .where(Sale.product_id == product_id, Sale.sale_date >= cutoff)
            .group_by(Sale.sale_date)
            .order_by(Sale.sale_date)
        )
        history = []
        for row in result.all():
            history.append({
                "date": row[0].isoformat(),
                "quantity": float(row[1]),
                "revenue": round(float(row[2]), 2),
            })
        return history

    async def _get_total_revenue(self, days: int, store_id: Optional[int] = None) -> float:
        if days == 0:
            q = select(func.coalesce(func.sum(Sale.total_price), 0.0)).where(
                Sale.sale_date == self.today
            )
        else:
            cutoff = self.today - timedelta(days=days)
            q = select(func.coalesce(func.sum(Sale.total_price), 0.0)).where(
                Sale.sale_date >= cutoff
            )
        if store_id:
            q = q.where(Sale.store_id == store_id)
        result = await self.db.execute(q)
        return round(float(result.scalar()), 2)
