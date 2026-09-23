"""
ScanIZI — AI Excel Analyzer
Uses Gemini to intelligently analyze Excel/CSV files:
  1. Understand arbitrary column headers (any language, any format)
  2. Map them to the ScanIZI product schema
  3. Suggest product categories based on names
  4. Return enriched import mapping + a summary of what it found

This module is called BEFORE the actual import, to give the user
a preview of what the AI understood from their file.
"""

import io
import json
import logging
import csv
from typing import Dict, Any, List, Optional

from app.core.config import settings
from app.ai.analyzer import _gemini_available, _gemini_client

logger = logging.getLogger(__name__)

# The ScanIZI product schema fields with descriptions
SCHEMA_DESCRIPTION = """
ScanIZI Product Schema (JSON field names):
- name: Product name/title (REQUIRED)
- sku: Article number / internal code / SKU
- barcode: Barcode (EAN-13, EAN-8, QR, etc.)
- purchase_price: Purchase cost / wholesale price (numeric, in any currency)
- sale_price: Retail sale price (numeric)
- quantity: Current stock quantity / inventory count (numeric)
- category: Product category / group / department
- unit: Unit of measurement (шт., кг, л, м, уп., etc.)
"""

EXCEL_ANALYZER_SYSTEM_PROMPT = """Ты — AI-аналитик системы ScanIZI для импорта товарных данных.

Пользователь загрузил Excel или CSV файл с данными товаров.
Твоя задача:
1. Проанализировать заголовки столбцов
2. Сопоставить их с полями схемы базы данных ScanIZI
3. Дать краткий анализ содержимого файла
4. Вернуть структурированный JSON ответ

ВАЖНО: Заголовки могут быть на любом языке (русский, английский, узбекский, казахский).
Заголовки могут иметь нестандартные названия — используй контекст и примеры данных.

Ответь СТРОГО в формате JSON (без markdown-фенсов):
{
  "column_mapping": {
    "<заголовок_из_файла>": "<поле_схемы_или_null>"
  },
  "detected_fields": ["name", "sku", ...],
  "missing_required": ["name"],
  "file_quality": "good|ok|poor",
  "quality_reason": "<краткое объяснение>",
  "product_count_estimate": <число>,
  "detected_categories": ["категория1", "категория2"],
  "ai_summary": "<2-3 предложения о содержимом файла>",
  "import_ready": true/false,
  "warnings": ["предупреждение 1", "предупреждение 2"]
}

Допустимые значения для column_mapping:
name, sku, barcode, purchase_price, sale_price, quantity, category, unit, null
Используй null если столбец не соответствует ни одному полю схемы.
"""


async def analyze_excel_with_ai(
    headers: List[str],
    sample_rows: List[Dict[str, Any]],
    total_rows: int,
) -> Dict[str, Any]:
    """
    Ask Gemini to analyze the uploaded Excel file structure and
    return an intelligent column mapping + summary.

    Args:
        headers: List of column header strings from the file
        sample_rows: First 5-10 rows as list of dicts (header->value)
        total_rows: Total number of data rows in the file

    Returns:
        Dict with column_mapping, ai_summary, warnings, etc.
    """
    if not _gemini_available or not _gemini_client:
        return _fallback_excel_analysis(headers, sample_rows, total_rows)

    prompt = f"""Проанализируй Excel-файл с данными товаров.

{SCHEMA_DESCRIPTION}

Информация о файле:
- Всего строк с данными: {total_rows}
- Заголовки столбцов: {headers}

Примеры данных (первые строки):
{json.dumps(sample_rows[:8], ensure_ascii=False, indent=2)}

Определи какой столбец соответствует какому полю схемы ScanIZI.
Обрати внимание на примеры данных — они помогут понять смысл столбца.
"""

    try:
        response = _gemini_client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config={
                "system_instruction": EXCEL_ANALYZER_SYSTEM_PROMPT,
                "temperature": 0.1,  # Low temperature for consistent mapping
                "max_output_tokens": 1500,
            },
        )

        text = response.text.strip()
        # Strip markdown if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json) and last line (```)
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        if text.lower().startswith("json"):
            text = text[4:].strip()

        result = json.loads(text)

        # Validate required keys
        if "column_mapping" not in result:
            logger.warning("AI Excel analysis missing column_mapping")
            return _fallback_excel_analysis(headers, sample_rows, total_rows)

        # Ensure all original headers are in the mapping
        for h in headers:
            if h not in result["column_mapping"]:
                result["column_mapping"][h] = None

        result["source"] = "ai"
        result["total_rows"] = total_rows
        return result

    except json.JSONDecodeError as e:
        logger.error(f"AI Excel JSON parse error: {e}")
        return _fallback_excel_analysis(headers, sample_rows, total_rows)
    except Exception as e:
        logger.error(f"AI Excel analysis failed: {e}")
        return _fallback_excel_analysis(headers, sample_rows, total_rows)


def _fallback_excel_analysis(
    headers: List[str],
    sample_rows: List[Dict],
    total_rows: int,
) -> Dict[str, Any]:
    """
    Rule-based fallback column mapping when AI is unavailable.
    Uses the same keyword matching as the original ExcelConnector.
    """
    from app.connectors.excel import COLUMN_MAPPING

    column_mapping = {}
    detected_fields = []

    for header in headers:
        normalized = str(header).strip().lower()
        mapped_field = None
        for pattern, field in COLUMN_MAPPING.items():
            if pattern in normalized:
                mapped_field = field
                break
        column_mapping[header] = mapped_field
        if mapped_field and mapped_field not in detected_fields:
            detected_fields.append(mapped_field)

    has_name = "name" in detected_fields
    has_price = "sale_price" in detected_fields or "purchase_price" in detected_fields
    missing_required = []
    if not has_name:
        missing_required.append("name")

    if has_name and len(detected_fields) >= 3:
        quality = "good"
        quality_reason = "Обнаружены основные поля"
    elif has_name:
        quality = "ok"
        quality_reason = "Обнаружено только название товара"
    else:
        quality = "poor"
        quality_reason = "Не удалось определить столбец с названием товара"

    return {
        "column_mapping": column_mapping,
        "detected_fields": detected_fields,
        "missing_required": missing_required,
        "file_quality": quality,
        "quality_reason": quality_reason,
        "product_count_estimate": total_rows,
        "detected_categories": [],
        "ai_summary": (
            f"Файл содержит {total_rows} строк. "
            f"Обнаружено {len(detected_fields)} поддерживаемых полей: {', '.join(detected_fields) or 'нет'}. "
            "AI-анализ недоступен — используется стандартная логика сопоставления."
        ),
        "import_ready": has_name,
        "warnings": (
            ["Не удалось определить столбец с названием товара"] if not has_name else []
        ),
        "source": "fallback",
        "total_rows": total_rows,
    }


async def read_file_for_analysis(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Read Excel or CSV file and extract headers + sample rows for AI analysis.
    Returns: { headers, sample_rows, total_rows, file_type }
    """
    filename_lower = filename.lower()

    try:
        if filename_lower.endswith(".csv"):
            return _read_csv_for_analysis(file_bytes)
        else:
            return await _read_excel_for_analysis(file_bytes)
    except Exception as e:
        logger.error(f"File read error: {e}")
        return {"error": f"Ошибка чтения файла: {str(e)}"}


def _read_csv_for_analysis(file_bytes: bytes) -> Dict[str, Any]:
    """Read CSV and return headers + sample rows."""
    # Try different encodings
    for encoding in ["utf-8-sig", "utf-8", "cp1251", "latin-1"]:
        try:
            text = file_bytes.decode(encoding)
            reader = csv.DictReader(io.StringIO(text))
            headers = [str(h).strip() for h in (reader.fieldnames or [])]
            all_rows = list(reader)
            sample = [
                {str(k).strip(): str(v).strip() for k, v in row.items()}
                for row in all_rows[:10]
            ]
            return {
                "headers": headers,
                "sample_rows": sample,
                "total_rows": len(all_rows),
                "file_type": "csv",
            }
        except (UnicodeDecodeError, Exception):
            continue

    return {"error": "Не удалось прочитать CSV файл. Проверьте кодировку (UTF-8 или Windows-1251)."}


async def _read_excel_for_analysis(file_bytes: bytes) -> Dict[str, Any]:
    """Read Excel (.xlsx/.xls) and return headers + sample rows."""
    try:
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))

        if not rows:
            return {"error": "Файл пустой."}

        headers = [str(h).strip() if h is not None else f"col_{i}" for i, h in enumerate(rows[0])]
        data_rows = rows[1:]
        total_rows = len(data_rows)

        sample = []
        for row in data_rows[:10]:
            row_dict = {}
            for i, val in enumerate(row):
                if i < len(headers):
                    row_dict[headers[i]] = str(val).strip() if val is not None else ""
            sample.append(row_dict)

        wb.close()
        return {
            "headers": headers,
            "sample_rows": sample,
            "total_rows": total_rows,
            "file_type": "xlsx",
        }
    except Exception as e:
        return {"error": f"Ошибка чтения Excel: {str(e)}"}
