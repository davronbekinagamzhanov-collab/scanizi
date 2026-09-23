"""
ScanIZI Decision Engine — Scorer
Composite risk scoring using multiple factors (not hard rules).
"""

from typing import Dict, Any


def compute_risk_score(metrics: Dict[str, Any]) -> int:
    """
    Compute composite risk score (0-100) for a product.
    Higher score = more attention needed.
    
    Uses multi-factor scoring — NOT simple threshold rules.
    """
    score = 0.0

    inv_value = metrics.get("inventory_value", 0)
    sales_30d = metrics.get("sales_30d", 0)
    sales_90d = metrics.get("sales_90d", 0)
    days_without_sale = metrics.get("days_without_sale", 0)
    turnover_days = metrics.get("turnover_days", 9999)
    sales_change = metrics.get("sales_change_percent", 0)
    days_of_stock = metrics.get("days_of_stock", 9999)
    is_seasonal = metrics.get("is_seasonal", False)
    season_months = metrics.get("season_months", [])
    current_month = metrics.get("current_month", 1)

    # Factor 1: Inventory value weight (0-25 points)
    # Higher value = more capital at risk
    if inv_value > 500000:
        score += 25
    elif inv_value > 200000:
        score += 20
    elif inv_value > 50000:
        score += 15
    elif inv_value > 10000:
        score += 10
    elif inv_value > 1000:
        score += 5

    # Factor 2: Sales velocity (0-25 points)
    # Low sales relative to stock = frozen capital risk
    if sales_30d == 0 and inv_value > 0:
        if not is_seasonal or current_month in season_months:
            score += 25
        else:
            score += 10  # Off-season — reduce penalty
    elif turnover_days > 365:
        score += 20
    elif turnover_days > 180:
        score += 15
    elif turnover_days > 90:
        score += 10
    elif turnover_days > 60:
        score += 5

    # Factor 3: Sales trend (0-20 points)
    # Declining sales = growing risk
    if sales_change < -50:
        score += 20
    elif sales_change < -30:
        score += 15
    elif sales_change < -15:
        score += 10
    elif sales_change > 30 and days_of_stock < 14:
        score += 15  # Growing demand + low stock = deficit risk

    # Factor 4: Days without sale (0-15 points)
    if days_without_sale > 180 and not is_seasonal:
        score += 15
    elif days_without_sale > 90:
        score += 10 if not is_seasonal else 5
    elif days_without_sale > 60:
        score += 7
    elif days_without_sale > 30:
        score += 3

    # Factor 5: Deficit risk (0-15 points)
    if days_of_stock < 7 and sales_30d > 0:
        score += 15
    elif days_of_stock < 14 and sales_30d > 0:
        score += 10
    elif days_of_stock < 30 and sales_30d > 5:
        score += 5

    return min(100, max(0, int(score)))


def determine_recommendation_type(metrics: Dict[str, Any], risk_score: int) -> str:
    """
    Determine recommendation type based on multi-factor analysis.
    Returns one of the fixed recommendation types.
    """
    inv_value = metrics.get("inventory_value", 0)
    total_qty = metrics.get("total_quantity", 0)
    sales_30d = metrics.get("sales_30d", 0)
    sales_90d = metrics.get("sales_90d", 0)
    days_of_stock = metrics.get("days_of_stock", 9999)
    turnover_days = metrics.get("turnover_days", 9999)
    sales_change = metrics.get("sales_change_percent", 0)
    days_without_sale = metrics.get("days_without_sale", 0)
    is_seasonal = metrics.get("is_seasonal", False)
    season_months = metrics.get("season_months", [])
    current_month = metrics.get("current_month", 1)
    inventory_by_warehouse = metrics.get("inventory_by_warehouse", [])

    # Check for transfer opportunity (multi-store imbalance)
    if len(inventory_by_warehouse) >= 2:
        qtys = [w["quantity"] for w in inventory_by_warehouse]
        if max(qtys) > min(qtys) * 5 and min(qtys) < 20:
            return "CONSIDER_TRANSFER"

    # Deficit risk — need to restock
    if days_of_stock < 14 and sales_30d > 5 and total_qty > 0:
        return "RESTOCK"

    if days_of_stock < 7 and sales_30d > 0:
        return "RESTOCK"

    # Dead/frozen stock
    if (turnover_days > 180 and inv_value > 10000
            and not (is_seasonal and current_month not in season_months)):
        if inv_value > 100000:
            return "CONSIDER_RETURN"
        return "CONSIDER_DISCOUNT"

    # Slow moving with significant value
    if turnover_days > 120 and inv_value > 5000:
        return "CONSIDER_DISCOUNT"

    # No sales but not seasonal issue
    if days_without_sale > 90 and inv_value > 5000 and not is_seasonal:
        return "DO_NOT_PURCHASE"

    # High stock, declining demand
    if sales_change < -30 and turnover_days > 60 and inv_value > 5000:
        return "DO_NOT_PURCHASE"

    # Low risk — observe
    if risk_score > 20:
        return "OBSERVE"

    return "NO_ACTION"


def determine_confidence(metrics: Dict[str, Any], risk_score: int) -> str:
    """Determine confidence level based on data availability."""
    sales_90d = metrics.get("sales_90d", 0)
    sales_365d = metrics.get("sales_365d", 0)

    if sales_365d > 50:
        return "high"
    elif sales_90d > 10:
        return "medium"
    elif sales_90d > 0:
        return "low"
    else:
        return "low"
