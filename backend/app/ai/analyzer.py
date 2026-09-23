"""
ScanIZI AI Layer — Gemini API Integration (gemini-3.8-flash)
Отвечает на вопрос: «Почему это важно и какое действие стоит рассмотреть?»

AI получает ТОЛЬКО проверенные и рассчитанные метрики из Analytics Engine.
AI возвращает структурированный JSON: recommendation, reason, evidence, confidence.
При отсутствии GEMINI_API_KEY используется честный fallback.
"""

import json
import logging
from typing import Dict, Any, Optional, List

from app.core.config import settings
from app.decision_engine.prioritizer import REC_TYPE_LABELS

logger = logging.getLogger(__name__)

# Try to import Gemini SDK
_gemini_available = False
_gemini_client = None

try:
    from google import genai
    if settings.GEMINI_API_KEY:
        _gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        _gemini_available = True
        logger.info("Gemini API initialized successfully")
    else:
        logger.warning("GEMINI_API_KEY not set — AI will use analytics fallback")
except ImportError:
    logger.warning("google-genai not installed — AI will use analytics fallback")
except Exception as e:
    logger.warning(f"Gemini API init failed: {e} — AI will use analytics fallback")


SYSTEM_PROMPT = """Ты — AI-аналитик системы ScanIZI, интеллектуальной системы анализа товаров и запасов для магазинов.

Твоя задача — проанализировать метрики конкретного товара и дать структурированную рекомендацию владельцу бизнеса.

ПРАВИЛА:
1. Все числа УЖЕ рассчитаны аналитическим модулем. НЕ считай арифметику заново.
2. Используй ТОЛЬКО предоставленные данные. НЕ придумывай цифры.
3. Отвечай ТОЛЬКО на русском языке.
4. Рекомендация должна быть мягкой — ты предлагаешь рассмотреть действие, а не принимаешь решение.
5. НЕ используй агрессивные формулировки вроде «СРОЧНО ПРОДАЙТЕ».
6. Учитывай сезонность, если товар сезонный.
7. Если данных недостаточно для надёжного вывода, скажи об этом.

Типы рекомендаций (используй строго один из них):
- ПОПОЛНИТЬ
- НАБЛЮДАТЬ  
- РАССМОТРЕТЬ СКИДКУ
- РАССМОТРЕТЬ ВОЗВРАТ
- РАССМОТРЕТЬ ПЕРЕМЕЩЕНИЕ
- НЕ ЗАКУПАТЬ ПОКА
- НЕТ ДЕЙСТВИЙ

Ответь СТРОГО в формате JSON (без markdown):
{
  "recommendation": "<тип рекомендации>",
  "reason": "<объяснение почему товар требует внимания, 2-4 предложения>",
  "evidence": {
    "key_metrics": ["<список ключевых метрик, на которых основан вывод>"],
    "what_happened": "<что произошло>",
    "why_important": "<почему это важно>",
    "what_to_do": "<что можно сделать>"
  },
  "confidence": "<low|medium|high>"
}"""


async def analyze_product_with_ai(metrics: Dict[str, Any]) -> Optional[Dict]:
    """
    Send product metrics to Gemini API for analysis.
    Returns structured JSON with recommendation, reason, evidence, confidence.
    Falls back to analytics-only if AI is unavailable.
    """
    if not _gemini_available or not _gemini_client:
        return _generate_fallback_analysis(metrics)

    # Prepare only the relevant metrics for AI (not the entire database)
    product_summary = _prepare_metrics_for_ai(metrics)

    prompt = f"""Проанализируй следующий товар и дай рекомендацию:

{json.dumps(product_summary, ensure_ascii=False, indent=2)}

Определи тип рекомендации и объясни причину. Ответь строго в JSON-формате."""

    try:
        response = _gemini_client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
            config={
                "system_instruction": SYSTEM_PROMPT,
                "temperature": 0.3,
                "max_output_tokens": 1024,
            },
        )

        # Parse AI response
        text = response.text.strip()
        # Remove markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

        ai_result = json.loads(text)

        # Validate required fields
        required = ["recommendation", "reason", "evidence", "confidence"]
        for field in required:
            if field not in ai_result:
                logger.warning(f"AI response missing field: {field}")
                return _generate_fallback_analysis(metrics)

        ai_result["source"] = "ai"
        return ai_result

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI JSON response: {e}")
        return _generate_fallback_analysis(metrics)
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return _generate_fallback_analysis(metrics)


async def analyze_batch_with_ai(
    attention_items: List[Dict[str, Any]]
) -> List[Dict]:
    """Analyze multiple high-priority items with AI."""
    results = []
    for item in attention_items[:10]:  # Limit to top 10
        result = await analyze_product_with_ai(item)
        if result:
            result["product_id"] = item.get("product_id")
            result["product_name"] = item.get("product_name")
            results.append(result)
    return results


def is_ai_available() -> bool:
    """Check if AI API is available."""
    return _gemini_available


def _prepare_metrics_for_ai(metrics: Dict[str, Any]) -> Dict:
    """Prepare a clean subset of metrics for AI — only what it needs."""
    return {
        "название": metrics.get("product_name", ""),
        "артикул": metrics.get("sku", ""),
        "цена_закупки": metrics.get("purchase_price", 0),
        "цена_продажи": metrics.get("sale_price", 0),
        "маржа_процент": metrics.get("margin_percent", 0),
        "остаток_шт": metrics.get("total_quantity", 0),
        "стоимость_остатка": metrics.get("inventory_value", 0),
        "продажи_7_дней": metrics.get("sales_7d", 0),
        "продажи_30_дней": metrics.get("sales_30d", 0),
        "продажи_90_дней": metrics.get("sales_90d", 0),
        "изменение_продаж_процент": metrics.get("sales_change_percent", 0),
        "дней_без_продажи": metrics.get("days_without_sale", 0),
        "скорость_продаж_в_день": metrics.get("sales_velocity", 0),
        "оборачиваемость_дней": metrics.get("turnover_days", 0),
        "запас_на_дней": metrics.get("days_of_stock", 0),
        "тренд": metrics.get("trend", "stable"),
        "риск_дефицита": metrics.get("deficit_risk", False),
        "сезонный": metrics.get("is_seasonal", False),
        "склады": [
            {
                "магазин": w.get("store_name", ""),
                "склад": w.get("warehouse_name", ""),
                "количество": w.get("quantity", 0),
            }
            for w in metrics.get("inventory_by_warehouse", [])
        ],
    }


def _generate_fallback_analysis(metrics: Dict[str, Any]) -> Dict:
    """
    Generate analysis from Decision Engine when AI is unavailable.
    Honest fallback — no fake AI.
    """
    rec_type = metrics.get("rec_type", "OBSERVE")
    rec_label = metrics.get("rec_type_label", REC_TYPE_LABELS.get(rec_type, rec_type))

    # Build explanation based on metrics
    reasons = []
    evidence_metrics = []

    inv_value = metrics.get("inventory_value", 0)
    sales_30d = metrics.get("sales_30d", 0)
    sales_change = metrics.get("sales_change_percent", 0)
    days_without_sale = metrics.get("days_without_sale", 0)
    turnover_days = metrics.get("turnover_days", 9999)
    days_of_stock = metrics.get("days_of_stock", 9999)

    if rec_type == "RESTOCK":
        reasons.append(f"Товар имеет высокую скорость продаж ({sales_30d} шт. за 30 дней)")
        reasons.append(f"Текущий запас обеспечивает покрытие на {int(days_of_stock)} дней")
        reasons.append("Есть риск дефицита при текущей скорости продаж")
        evidence_metrics = ["продажи_30д", "запас_на_дней", "скорость_продаж"]
    elif rec_type in ["CONSIDER_DISCOUNT", "CONSIDER_RETURN"]:
        reasons.append(f"Стоимость остатка составляет {int(inv_value):,} ₸")
        if sales_30d == 0:
            reasons.append(f"За последние 30 дней продаж не было")
        else:
            reasons.append(f"Продажи за 30 дней: {sales_30d} шт.")
        if days_without_sale > 30:
            reasons.append(f"Последняя продажа была {days_without_sale} дней назад")
        evidence_metrics = ["стоимость_остатка", "продажи_30д", "дней_без_продажи", "оборачиваемость"]
    elif rec_type == "DO_NOT_PURCHASE":
        reasons.append(f"Текущий запас покрывает {int(days_of_stock)} дней при текущей скорости продаж")
        if sales_change < -20:
            reasons.append(f"Продажи снизились на {abs(int(sales_change))}%")
        evidence_metrics = ["запас_на_дней", "изменение_продаж", "оборачиваемость"]
    elif rec_type == "CONSIDER_TRANSFER":
        reasons.append("Обнаружен дисбаланс остатков между магазинами")
        wh = metrics.get("inventory_by_warehouse", [])
        if wh:
            qtys = [w["quantity"] for w in wh]
            reasons.append(f"Разница в остатках: от {int(min(qtys))} до {int(max(qtys))} шт.")
        evidence_metrics = ["остатки_по_складам", "продажи_по_магазинам"]
    else:
        reasons.append("Товар находится в нормальном состоянии")
        evidence_metrics = ["продажи_30д", "остаток", "тренд"]

    return {
        "recommendation": rec_label,
        "reason": ". ".join(reasons) + ".",
        "evidence": {
            "key_metrics": evidence_metrics,
            "what_happened": reasons[0] if reasons else "",
            "why_important": reasons[1] if len(reasons) > 1 else "",
            "what_to_do": f"Рекомендация: {rec_label}",
        },
        "confidence": metrics.get("confidence", "medium"),
        "source": "analytics",
        "_fallback_notice": "AI-анализ временно недоступен. Показаны результаты аналитического модуля.",
    }
