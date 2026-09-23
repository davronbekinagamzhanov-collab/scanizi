"""
ScanIZI — Portfolio Analyzer
Provides high-level business portfolio insights using Gemini API with structured JSON output.
When AI is unavailable, returns a rule-based analytics fallback.
"""

import json
import logging
from typing import Dict, Any, List, Optional

from app.core.config import settings
from app.ai.analyzer import _gemini_available, _gemini_client

logger = logging.getLogger(__name__)

PORTFOLIO_SYSTEM_PROMPT = """Ты — AI-аналитик бизнеса в системе ScanIZI.
Твоя задача — дать ВЫСОКОУРОВНЕВЫЙ анализ всего товарного портфеля бизнеса на основе агрегированных метрик.

ПРАВИЛА:
1. Используй ТОЛЬКО предоставленные метрики. Не придумывай числа.
2. Отвечай ТОЛЬКО на русском языке.
3. Анализируй с точки зрения здоровья всего бизнеса, а не отдельных товаров.
4. Будь конкретным и деловым.
5. Ответ СТРОГО в JSON-формате без markdown.

Ответь в следующем JSON формате:
{
  "health_score": <число от 0 до 100>,
  "health_label": "<Отлично|Хорошо|Требует внимания|Критично>",
  "summary": "<2-3 предложения общей оценки бизнеса>",
  "top_risks": [
    "<риск 1>",
    "<риск 2>",
    "<риск 3>"
  ],
  "top_opportunities": [
    "<возможность 1>",
    "<возможность 2>"
  ],
  "cash_flow_insight": "<1-2 предложения о денежном потоке>",
  "inventory_insight": "<1-2 предложения об остатках>",
  "priority_action": "<самое важное действие которое нужно предпринять>",
  "source": "ai"
}"""


async def analyze_portfolio(portfolio_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze the entire product portfolio and return high-level business insights.
    Uses Gemini AI if available, falls back to rule-based analytics.
    """
    if not _gemini_available or not _gemini_client:
        return _fallback_portfolio_analysis(portfolio_metrics)

    prompt = f"""Проанализируй товарный портфель бизнеса на основе следующих метрик:

{json.dumps(portfolio_metrics, ensure_ascii=False, indent=2)}

Дай высокоуровневую оценку здоровья бизнеса и ключевые инсайты."""

    try:
        response = _gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config={
                "system_instruction": PORTFOLIO_SYSTEM_PROMPT,
                "temperature": 0.25,
                "max_output_tokens": 1024,
            },
        )

        text = response.text.strip()
        # Strip markdown fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
        if text.startswith("json"):
            text = text[4:].strip()

        result = json.loads(text)

        # Validate required fields
        required = ["health_score", "health_label", "summary", "priority_action"]
        for field in required:
            if field not in result:
                logger.warning(f"Portfolio AI response missing field: {field}")
                return _fallback_portfolio_analysis(portfolio_metrics)

        result["source"] = "ai"
        return result

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse portfolio AI JSON: {e}")
        return _fallback_portfolio_analysis(portfolio_metrics)
    except Exception as e:
        logger.error(f"Portfolio Gemini API error: {e}")
        return _fallback_portfolio_analysis(portfolio_metrics)


def _fallback_portfolio_analysis(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Rule-based portfolio analysis when AI is unavailable.
    Provides honest business insights from computed metrics.
    """
    total_value = metrics.get("total_inventory_value", 0)
    frozen = metrics.get("frozen_capital", 0)
    frozen_pct = metrics.get("frozen_capital_percent", 0)
    sales_30d = metrics.get("sales_30d", 0)
    at_risk = metrics.get("products_at_risk", 0)
    deficit = metrics.get("potential_deficit", 0)
    total_products = metrics.get("total_products", 0)
    turnover_days = metrics.get("turnover_days", 0)
    avg_stock_age = metrics.get("avg_stock_age_days", 0)

    # Compute health score (0-100)
    score = 80
    risks = []
    opportunities = []

    # Deduct for frozen capital
    if frozen_pct > 40:
        score -= 25
        risks.append(f"Критически высокая доля замороженного капитала: {frozen_pct:.1f}% от остатков ({_fmt_currency(frozen)})")
    elif frozen_pct > 20:
        score -= 15
        risks.append(f"Повышенная доля замороженного капитала: {frozen_pct:.1f}% ({_fmt_currency(frozen)})")
    elif frozen_pct > 10:
        score -= 5

    # Deduct for deficit risk
    if deficit > 5:
        score -= 15
        risks.append(f"{deficit} товаров с риском дефицита (запас менее 14 дней)")
    elif deficit > 0:
        score -= 7
        risks.append(f"{deficit} товаров имеют критически малый запас")

    # Deduct for high-risk products
    if at_risk > 10:
        score -= 10
        risks.append(f"{at_risk} товаров с высоким оборотом и значительными остатками")
    elif at_risk > 3:
        score -= 5
        risks.append(f"{at_risk} товаров требуют оптимизации по обороту")

    # Deduct for old stock
    if avg_stock_age > 120:
        score -= 10
        risks.append(f"Средний возраст остатков {int(avg_stock_age)} дней — высокий риск устаревания")
    elif avg_stock_age > 60:
        score -= 5

    # Add for good turnover
    if 20 <= turnover_days <= 45:
        score += 5
        opportunities.append("Хорошая оборачиваемость — можно рассмотреть увеличение закупок популярных позиций")

    # Sales opportunities
    if sales_30d > 0 and total_value > 0:
        sales_to_value = sales_30d / total_value
        if sales_to_value > 0.3:
            opportunities.append("Высокое соотношение продаж к остаткам — позиции хорошо реализуются")
        elif sales_to_value < 0.05:
            score -= 5
            risks.append("Низкое соотношение выручки к стоимости остатков")

    if total_products > 0 and len(opportunities) == 0:
        opportunities.append("Проведите ABC-анализ для выявления высокоприбыльных позиций")
        opportunities.append("Рассмотрите ценовую оптимизацию для медленно оборачивающихся товаров")

    score = max(0, min(100, score))

    if score >= 80:
        health_label = "Отлично"
    elif score >= 60:
        health_label = "Хорошо"
    elif score >= 40:
        health_label = "Требует внимания"
    else:
        health_label = "Критично"

    # Build summary
    summary_parts = [
        f"Портфель содержит {total_products} активных товаров на сумму {_fmt_currency(total_value)}."
    ]
    if frozen_pct > 15:
        summary_parts.append(f"{frozen_pct:.0f}% капитала заморожено в медленно оборачивающихся товарах.")
    if deficit > 0:
        summary_parts.append(f"Обнаружено {deficit} позиций с риском дефицита.")
    summary = " ".join(summary_parts)

    # Priority action
    if deficit > 3:
        priority = f"Срочно пополните запасы для {deficit} товаров с риском дефицита."
    elif frozen_pct > 30:
        priority = f"Разработайте план реализации замороженного капитала ({_fmt_currency(frozen)}) — рассмотрите скидки или возврат поставщику."
    elif at_risk > 5:
        priority = f"Проведите аудит {at_risk} товаров с высокой стоимостью остатков и низкой оборачиваемостью."
    else:
        priority = "Проведите регулярный обзор AI-рекомендаций для поддержания здоровья портфеля."

    return {
        "health_score": score,
        "health_label": health_label,
        "summary": summary,
        "top_risks": risks[:3] if risks else ["Критических проблем не обнаружено"],
        "top_opportunities": opportunities[:2],
        "cash_flow_insight": (
            f"Выручка за 30 дней: {_fmt_currency(sales_30d)}. "
            f"Оборачиваемость: {int(turnover_days)} дней."
            if sales_30d > 0 else "Данные о продажах за последние 30 дней отсутствуют."
        ),
        "inventory_insight": (
            f"Средний возраст остатков: {int(avg_stock_age)} дней. "
            f"Замороженный капитал: {frozen_pct:.1f}% ({_fmt_currency(frozen)})."
        ),
        "priority_action": priority,
        "source": "analytics",
        "_notice": "AI-анализ недоступен. Показаны результаты аналитического модуля.",
    }


def _fmt_currency(value: float) -> str:
    """Format number as KZT currency string."""
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M ₸"
    if value >= 1_000:
        return f"{int(value / 1_000)}K ₸"
    return f"{int(value)} ₸"


def prepare_portfolio_metrics(dashboard_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare a clean, AI-readable summary of portfolio metrics.
    Removes internal implementation details.
    """
    return {
        "total_products": dashboard_metrics.get("total_products", 0),
        "total_inventory_value_kzt": round(dashboard_metrics.get("total_inventory_value", 0), 0),
        "frozen_capital_kzt": round(dashboard_metrics.get("frozen_capital", 0), 0),
        "frozen_capital_percent": round(dashboard_metrics.get("frozen_capital_percent", 0), 1),
        "products_at_risk": dashboard_metrics.get("products_at_risk", 0),
        "potential_deficit_count": dashboard_metrics.get("potential_deficit", 0),
        "avg_stock_age_days": round(dashboard_metrics.get("avg_stock_age_days", 0), 0),
        "sales_30d_kzt": round(dashboard_metrics.get("sales_30d", 0), 0),
        "avg_turnover_days": round(dashboard_metrics.get("turnover_days", 0), 0),
    }
