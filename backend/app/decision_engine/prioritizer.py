"""
ScanIZI Decision Engine — Prioritizer
Ranks problems by financial impact × risk × urgency.
"""

from typing import List, Dict, Any
from app.decision_engine.scorer import compute_risk_score, determine_recommendation_type, determine_confidence


REC_TYPE_LABELS = {
    "RESTOCK": "Пополнить",
    "OBSERVE": "Наблюдать",
    "CONSIDER_DISCOUNT": "Рассмотреть скидку",
    "CONSIDER_RETURN": "Рассмотреть возврат",
    "CONSIDER_TRANSFER": "Рассмотреть перемещение",
    "DO_NOT_PURCHASE": "Не закупать пока",
    "NO_ACTION": "Нет действий",
}


def prioritize_products(all_metrics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Score, classify, and prioritize all products.
    Returns list sorted by priority (highest first).
    """
    results = []

    for metrics in all_metrics:
        risk_score = compute_risk_score(metrics)
        rec_type = determine_recommendation_type(metrics, risk_score)
        confidence = determine_confidence(metrics, risk_score)

        # Priority = risk_score weighted by financial impact
        inv_value = metrics.get("inventory_value", 0)
        financial_weight = min(1.0, inv_value / 100000) if inv_value > 0 else 0
        priority = int(risk_score * (0.6 + 0.4 * financial_weight))

        results.append({
            **metrics,
            "risk_score": risk_score,
            "rec_type": rec_type,
            "rec_type_label": REC_TYPE_LABELS.get(rec_type, rec_type),
            "confidence": confidence,
            "priority": priority,
            "financial_impact": inv_value if rec_type in [
                "CONSIDER_DISCOUNT", "CONSIDER_RETURN", "DO_NOT_PURCHASE"
            ] else 0,
        })

    results.sort(key=lambda x: x["priority"], reverse=True)
    return results


def get_attention_items(prioritized: List[Dict], limit: int = 5) -> List[Dict]:
    """Get top N items that require attention for the dashboard."""
    attention = []
    for item in prioritized:
        if item["rec_type"] == "NO_ACTION":
            continue
        if item["priority"] < 15:
            continue

        attention.append({
            "product_id": item["product_id"],
            "product_name": item["product_name"],
            "rec_type": item["rec_type"],
            "rec_type_label": item["rec_type_label"],
            "priority": item["priority"],
            "risk_score": item["risk_score"],
            "inventory_value": item["inventory_value"],
            "sales_30d": item["sales_30d"],
            "days_without_sale": item["days_without_sale"],
            "trend": item["trend"],
            "sales_change_percent": item["sales_change_percent"],
            "confidence": item["confidence"],
            "financial_impact": item.get("financial_impact", 0),
        })

        if len(attention) >= limit:
            break

    return attention
