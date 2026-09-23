# -*- coding: utf-8 -*-
"""
ScanIZI Backend Tests
Tests 4-25 per specification.
"""
import sys
import math

sys.path.insert(0, ".")

print("=== ScanIZI Backend Tests ===\n")

# ── Import tests ──────────────────────────────────────────────────────────────
try:
    from app.main import app
    print(f"TEST 1: Backend import OK — {len(app.routes)} routes")
except Exception as e:
    print(f"TEST 1 FAIL: {e}")
    sys.exit(1)

try:
    from app.connectors.excel import (
        _normalize_number, _normalize_str, _normalize_category,
        _build_mapping, COLUMN_MAPPING, ExcelConnector, CSVConnector
    )
    print("TEST 2: Excel connector import OK")
except Exception as e:
    print(f"TEST 2 FAIL: {e}")
    sys.exit(1)

# ── Health endpoint structure ─────────────────────────────────────────────────
try:
    from app.api import health
    print("TEST 3: Health endpoint module OK")
except Exception as e:
    print(f"TEST 3: Health check (direct): {e}")

# ── Column mapping tests ──────────────────────────────────────────────────────
# Russian headers
headers_ru = [
    "Название товара", "Артикул", "Штрихкод",
    "Цена", "Остаток", "Категория", "Единица"
]
m_ru = _build_mapping(headers_ru, {})
failed = []
if m_ru.get("Название товара") != "name": failed.append(f"name={m_ru.get('Название товара')}")
if m_ru.get("Артикул") != "sku": failed.append(f"sku={m_ru.get('Артикул')}")
if m_ru.get("Штрихкод") != "barcode": failed.append(f"barcode={m_ru.get('Штрихкод')}")
if m_ru.get("Цена") != "sale_price": failed.append(f"price={m_ru.get('Цена')}")
if m_ru.get("Остаток") != "quantity": failed.append(f"qty={m_ru.get('Остаток')}")
if m_ru.get("Категория") != "category": failed.append(f"cat={m_ru.get('Категория')}")
if m_ru.get("Единица") != "unit": failed.append(f"unit={m_ru.get('Единица')}")
if failed:
    print(f"TEST 4 FAIL: Russian headers: {failed}")
else:
    print("TEST 4: Russian headers mapping OK")

# English headers
headers_en = ["Product name", "SKU", "Barcode", "Retail Price", "Quantity", "Category", "Unit"]
m_en = _build_mapping(headers_en, {})
failed_en = []
if m_en.get("Product name") != "name": failed_en.append(f"name={m_en.get('Product name')}")
if m_en.get("SKU") != "sku": failed_en.append(f"sku={m_en.get('SKU')}")
if m_en.get("Barcode") != "barcode": failed_en.append(f"barcode={m_en.get('Barcode')}")
if m_en.get("Retail Price") != "sale_price": failed_en.append(f"sale_price={m_en.get('Retail Price')}")
if m_en.get("Quantity") != "quantity": failed_en.append(f"qty={m_en.get('Quantity')}")
if failed_en:
    print(f"TEST 5 FAIL: English headers: {failed_en}")
else:
    print("TEST 5: English headers mapping OK")

# Unusual headers
headers_weird = [
    "Наименование", "Код товара", "Себестоимость", "Цена продажи", "Кол-во"
]
m_weird = _build_mapping(headers_weird, {})
failed_weird = []
if m_weird.get("Наименование") != "name": failed_weird.append(f"name={m_weird.get('Наименование')}")
if m_weird.get("Код товара") != "sku": failed_weird.append(f"sku={m_weird.get('Код товара')}")
if m_weird.get("Себестоимость") != "purchase_price": failed_weird.append(f"cost={m_weird.get('Себестоимость')}")
if m_weird.get("Цена продажи") != "sale_price": failed_weird.append(f"sale_price={m_weird.get('Цена продажи')}")
if m_weird.get("Кол-во") != "quantity": failed_weird.append(f"qty={m_weird.get('Кол-во')}")
if failed_weird:
    print(f"TEST 6 FAIL: Unusual headers: {failed_weird}")
else:
    print("TEST 6: Unusual headers mapping OK")

# AI mapping priority
ai_map = {
    "Количество товара на складе": "quantity",
    "Торговое название": "name"
}
m_ai = _build_mapping(["Количество товара на складе", "Торговое название"], ai_map)
if m_ai.get("Количество товара на складе") == "quantity" and m_ai.get("Торговое название") == "name":
    print("TEST 7: AI mapping priority OK")
else:
    print(f"TEST 7 FAIL: AI mapping: {m_ai}")

# AI unavailable fallback (no key → fallback)
from app.ai.excel_analyzer import _fallback_excel_analysis
fb = _fallback_excel_analysis(
    ["Название", "Артикул", "Цена", "Остаток"],
    [{"Название": "iPhone", "Артикул": "IP001", "Цена": "50000", "Остаток": "10"}],
    1
)
if fb.get("source") == "fallback" and fb.get("import_ready") == True:
    print("TEST 8: AI fallback OK")
else:
    print(f"TEST 8 FAIL: Fallback result: {fb}")

# ── Number normalization ──────────────────────────────────────────────────────
tests_num = [
    ("1 200", 1200.0),
    ("1,200", 1200.0),
    ("1200.00", 1200.0),
    (1200, 1200.0),
    (None, None),
    ("nan", None),
    ("", None),
    ("—", None),
    ("н/д", None),
]
num_ok = True
for val, expected in tests_num:
    result = _normalize_number(val)
    if result != expected:
        print(f"  NORM FAIL: _normalize_number({val!r}) = {result!r}, expected {expected!r}")
        num_ok = False
# NaN float
if _normalize_number(float("nan")) is not None:
    print("  NORM FAIL: float('nan') should return None")
    num_ok = False
if num_ok:
    print("TEST 8b: Number normalization OK (all cases)")

# Category normalization
cat_tests = [
    ("электроника", "Электроника"),
    ("  ЭЛЕКТРОНИКА  ", "Электроника"),
    ("", ""),
    ("мобильные телефоны", "Мобильные Телефоны"),
]
cat_ok = True
for val, expected in cat_tests:
    result = _normalize_category(val)
    if result != expected:
        print(f"  CAT FAIL: _normalize_category({val!r}) = {result!r}, expected {expected!r}")
        cat_ok = False
if cat_ok:
    print("TEST 10: Category normalization OK")

# ── Test Excel connector import_data with openpyxl in-memory ─────────────────
import io
try:
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Название", "Артикул", "Штрихкод", "Цена продажи", "Себестоимость", "Остаток", "Категория"])
    ws.append(["iPhone 15", "IP001", "1234567890123", 50000, 35000, 10, "Телефоны"])
    ws.append(["Samsung A54", "SA001", "9876543210987", 35000, 25000, 5, "Телефоны"])
    ws.append(["Зарядное USB-C", "CH001", "", 2000, 1000, 100, "Аксессуары"])
    buf = io.BytesIO()
    wb.save(buf)
    excel_bytes = buf.getvalue()
    print("TEST 9 (Excel read): Created test Excel file in memory OK")
except Exception as e:
    print(f"TEST 9 FAIL: {e}")

# Connector validation
import asyncio

async def test_validate():
    connector = ExcelConnector()
    result = await connector.validate(excel_bytes)
    if result.get("valid") and result.get("total_rows") == 3:
        print(f"TEST 9: Excel validate OK — {result['total_rows']} rows, cols: {result['columns_detected']}")
    else:
        print(f"TEST 9 FAIL: {result}")

asyncio.run(test_validate())

# ── Snapshot import simulation ────────────────────────────────────────────────
# Build a second Excel to test quantity update 10→9
try:
    wb2 = openpyxl.Workbook()
    ws2 = wb2.active
    ws2.append(["Название", "Артикул", "Остаток"])
    ws2.append(["iPhone 15", "IP001", 9])  # Changed from 10 to 9
    buf2 = io.BytesIO()
    wb2.save(buf2)
    excel_bytes_update = buf2.getvalue()
    print("TEST 15: Snapshot Excel (quantity 9) created OK")
except Exception as e:
    print(f"TEST 15 FAIL: {e}")

# ── CSV connector ─────────────────────────────────────────────────────────────
async def test_csv():
    csv_data = "Название,Артикул,Цена,Остаток\nТовар Тест,T001,1000,50\n".encode("utf-8-sig")
    connector = CSVConnector()
    result = await connector.validate(csv_data)
    if result.get("valid") and result.get("total_rows", 0) >= 1:
        print(f"TEST 5b: CSV validate OK — {result['total_rows']} rows")
    else:
        print(f"TEST 5b FAIL: {result}")

asyncio.run(test_csv())

# ── POST /sales route exists ──────────────────────────────────────────────────
from app.api.routes import sales_router
post_routes = [r for r in sales_router.routes if "POST" in getattr(r, "methods", [])]
if post_routes:
    print(f"TEST 16: POST /sales endpoint exists OK ({len(post_routes)} POST routes)")
else:
    print("TEST 16 FAIL: No POST route in sales_router")

# ── AI modules import ─────────────────────────────────────────────────────────
try:
    from app.ai.analyzer import is_ai_available, analyze_product_with_ai
    from app.ai.portfolio_analyzer import analyze_portfolio
    from app.ai.excel_analyzer import analyze_excel_with_ai, read_file_for_analysis
    print("TEST 24: All AI modules import OK")
    print(f"         AI available: {is_ai_available()}")
except Exception as e:
    print(f"TEST 24 FAIL: {e}")

# ── Gemini no hardcoded model ─────────────────────────────────────────────────
import re
for filepath in [
    "app/ai/analyzer.py",
    "app/ai/portfolio_analyzer.py",
    "app/ai/excel_analyzer.py",
]:
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        hardcoded = re.findall(r'model="gemini[^"]*"', content)
        if hardcoded:
            print(f"  SECURITY: Hardcoded model in {filepath}: {hardcoded}")
        else:
            print(f"TEST 2b ({filepath}): No hardcoded model names OK")
    except FileNotFoundError:
        print(f"  SKIP: {filepath} not found")

print()
print("=== ALL BACKEND TESTS COMPLETE ===")
