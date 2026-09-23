"""
ScanIZI — Excel/CSV Import Connector
Full production implementation:
- AI-first column mapping with keyword fallback
- Snapshot import (quantity replaces, NOT adds)
- Full product upsert: SKU → barcode → create
- Category case-insensitive upsert (no duplicates)
- Inventory upsert (product+warehouse key, SET not ADD)
- Row-level error isolation (one bad row doesn't kill import)
- Data normalization: whitespace, numbers as strings, NaN guard
"""

import io
import csv
import math
import re
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from app.connectors.base import DataConnector
from app.models import Product, Category, Inventory, DataSource
from app.db.database import SyncSessionLocal


# ─── Keyword fallback mapping ──────────────────────────────────────────────
# Used when AI mapping is not available or as a supplement.
COLUMN_MAPPING = {
    # name
    "название": "name", "наименование": "name", "товар": "name", "name": "name",
    "product": "name", "товарное наименование": "name", "наим": "name",
    "описание": "name", "description": "name", "номенклатура": "name",
    # sku
    "артикул": "sku", "sku": "sku", "код": "sku", "code": "sku",
    "код товара": "sku", "internal code": "sku", "item code": "sku",
    "арт": "sku", "art": "sku",
    # barcode
    "штрихкод": "barcode", "barcode": "barcode", "штрих-код": "barcode",
    "ean": "barcode", "ean13": "barcode", "ean-13": "barcode",
    "штрих код": "barcode", "upc": "barcode", "gtin": "barcode",
    # purchase_price
    "цена_закупки": "purchase_price", "закупочная": "purchase_price",
    "себестоимость": "purchase_price", "purchase_price": "purchase_price",
    "cost": "purchase_price", "закупка": "purchase_price",
    "закупочная цена": "purchase_price", "оптовая цена": "purchase_price",
    "wholesale": "purchase_price",
    # sale_price
    "цена_продажи": "sale_price", "цена": "sale_price", "розничная": "sale_price",
    "sale_price": "sale_price", "price": "sale_price", "retail": "sale_price",
    "розничная цена": "sale_price", "цена продажи": "sale_price",
    "retail price": "sale_price", "selling price": "sale_price",
    # quantity
    "количество": "quantity", "остаток": "quantity", "кол-во": "quantity",
    "quantity": "quantity", "stock": "quantity", "qty": "quantity",
    "запас": "quantity", "кол": "quantity", "остатки": "quantity",
    "количество товара": "quantity", "остаток на складе": "quantity",
    # category
    "категория": "category", "category": "category", "группа": "category",
    "group": "category", "тип": "category", "type": "category",
    "подгруппа": "category", "раздел": "category", "section": "category",
    # unit
    "единица": "unit", "ед.": "unit", "unit": "unit", "ед": "unit",
    "единица измерения": "unit", "uom": "unit", "мера": "unit",
}


def _normalize_number(value: Any) -> Optional[float]:
    """Convert any number-like value to float. Returns None if not parseable.
    Handles both:
      - Comma as decimal separator: '1,5' → 1.5
      - Comma as thousands separator: '1,200' → 1200.0
      - Space as thousands separator: '1 200' → 1200.0
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if math.isnan(value) or math.isinf(value):
            return None
        return float(value)
    s = str(value).strip()
    if not s or s.lower() in ("none", "null", "nan", "inf", "-", "—", "н/д"):
        return None
    # Remove currency symbols
    s = re.sub(r"[₸₽$€£¥]", "", s).strip()
    # Determine if comma is thousands separator or decimal separator:
    # Comma = thousands separator if followed by exactly 3 digits (and no period)
    # e.g., '1,200' → 1200, '1,200,000' → 1200000, '1,5' → 1.5
    if ',' in s and '.' not in s:
        parts = s.split(',')
        # All parts after first are 3 digits → thousands separator
        if len(parts) >= 2 and all(re.match(r'^\d{3}$', p) for p in parts[1:]):
            s = s.replace(',', '')
        else:
            # Decimal comma: '1,5' → '1.5'
            s = s.replace(',', '.')
    # Remove remaining space thousands separators
    s = re.sub(r'\s+', '', s)
    try:
        return float(s)
    except ValueError:
        return None


def _normalize_str(value: Any) -> str:
    """Convert to clean string, strip whitespace."""
    if value is None:
        return ""
    s = str(value).strip()
    # Collapse internal whitespace
    s = re.sub(r"\s+", " ", s)
    return s if s.lower() not in ("none", "null", "nan") else ""


def _normalize_category(name: str) -> str:
    """Normalize category name: strip, collapse spaces, title-case."""
    s = _normalize_str(name)
    if not s:
        return ""
    # Title case for first char of each word
    return " ".join(w.capitalize() for w in s.split())


def _build_mapping(headers: List[str], ai_mapping: Dict[str, str]) -> Dict[str, str]:
    """
    Build the final header→field mapping.
    AI mapping takes priority; keyword fallback for unmapped headers.
    Patterns sorted longest-first to prevent 'код' from shadowing 'штрихкод'.
    """
    # Sort patterns from longest to shortest to prefer more specific matches
    sorted_patterns = sorted(COLUMN_MAPPING.keys(), key=len, reverse=True)

    result = {}
    for header in headers:
        h_key = str(header).strip()
        # 1. AI mapping (exact header)
        if h_key in ai_mapping and ai_mapping[h_key]:
            result[h_key] = ai_mapping[h_key]
            continue
        # 2. Keyword fallback: exact lower match first
        h_lower = h_key.lower()
        matched = None
        if h_lower in COLUMN_MAPPING:
            matched = COLUMN_MAPPING[h_lower]
        else:
            # Substring match, longest pattern first
            for pattern in sorted_patterns:
                if pattern in h_lower:
                    matched = COLUMN_MAPPING[pattern]
                    break
        if matched:
            result[h_key] = matched
    return result


class ExcelConnector(DataConnector):
    def get_name(self) -> str:
        return "Excel"

    def get_type(self) -> str:
        return "file"

    def get_status(self) -> str:
        return "not_connected"

    async def connect(self, config: Optional[Dict] = None) -> bool:
        return True

    async def validate(self, data: Any) -> Dict[str, Any]:
        """Validate Excel file and return preview."""
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
            ws = wb.active

            rows = list(ws.iter_rows(values_only=True))
            wb.close()
            if not rows:
                return {"valid": False, "message": "Файл пустой."}

            headers = [_normalize_str(h) for h in rows[0]]
            mapping = _build_mapping(headers, {})

            data_rows = rows[1:]
            valid_rows = 0
            errors = []

            for idx, row in enumerate(data_rows[:1000], start=2):
                row_data = dict(zip(headers, row))
                name_col = next((h for h, f in mapping.items() if f == "name"), None)
                if name_col and _normalize_str(row_data.get(name_col)):
                    valid_rows += 1
                else:
                    errors.append({"row": idx, "error": "Отсутствует название товара"})

            preview = []
            for row in data_rows[:10]:
                preview.append({
                    str(h): (_normalize_str(v) if v is not None else "")
                    for h, v in zip(headers, row)
                })

            return {
                "valid": True,
                "columns_detected": headers,
                "column_mapping": mapping,
                "total_rows": len(data_rows),
                "valid_rows": valid_rows,
                "error_rows": len(errors),
                "errors": errors[:20],
                "preview_data": preview,
            }
        except Exception as e:
            return {"valid": False, "message": f"Ошибка чтения файла: {str(e)}"}

    async def import_data(
        self,
        file_data: bytes = None,
        mapping: Dict = None,
        warehouse_id: int = 1,
        **kwargs,
    ) -> Dict[str, Any]:
        """Import products from Excel file with snapshot semantics."""
        if not file_data:
            return {"success": False, "message": "Файл не предоставлен."}

        try:
            import openpyxl
            wb = openpyxl.load_workbook(
                io.BytesIO(file_data), read_only=True, data_only=True
            )
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            wb.close()

            if not rows:
                return {"success": False, "message": "Файл пустой."}

            headers = [_normalize_str(h) for h in rows[0]]
            return self._process_rows(headers, rows[1:], mapping or {}, warehouse_id)

        except Exception as e:
            return {"success": False, "message": f"Ошибка импорта: {str(e)}"}

    def _process_rows(
        self,
        headers: List[str],
        data_rows,
        ai_mapping: Dict,
        warehouse_id: int,
    ) -> Dict[str, Any]:
        """
        Process rows with full upsert + snapshot inventory.
        - Product upsert: match by SKU, then barcode, then create
        - Inventory upsert: SET quantity (snapshot, not accumulate)
        - Category upsert: case-insensitive, no duplicates
        - Row errors are isolated; bad row ≠ failed import
        """
        db = SyncSessionLocal()
        imported = 0
        updated = 0
        errors = []

        # Build final column→field mapping
        col_map = _build_mapping(headers, ai_mapping)

        # Cache: category_name_lower → Category.id
        category_cache: Dict[str, int] = {}

        try:
            for idx, row in enumerate(data_rows, start=2):
                try:
                    row_data = dict(zip(headers, row))

                    # Apply mapping to get normalized field values
                    mapped: Dict[str, Any] = {}
                    for header, value in row_data.items():
                        field = col_map.get(header)
                        if field:
                            mapped[field] = value

                    # ─── Required: name ────────────────────────
                    name = _normalize_str(mapped.get("name", ""))
                    if not name:
                        errors.append({
                            "row": idx,
                            "error": "Пропущено название товара",
                            "data": str(row_data)[:120],
                        })
                        continue

                    # ─── SKU / barcode ─────────────────────────
                    sku_raw = _normalize_str(mapped.get("sku", ""))
                    barcode_raw = _normalize_str(mapped.get("barcode", ""))
                    sku = sku_raw or f"IMP-{idx:06d}"
                    barcode = barcode_raw or None

                    # ─── Prices ────────────────────────────────
                    purchase_price = _normalize_number(mapped.get("purchase_price")) or 0.0
                    sale_price = _normalize_number(mapped.get("sale_price")) or 0.0

                    # ─── Quantity (snapshot) ───────────────────
                    qty_raw = _normalize_number(mapped.get("quantity"))
                    qty = qty_raw if qty_raw is not None else 0.0
                    if qty < 0:
                        qty = 0.0

                    # ─── Unit ──────────────────────────────────
                    unit = _normalize_str(mapped.get("unit", "шт.")) or "шт."

                    # ─── Category (case-insensitive upsert) ────
                    cat_name_raw = _normalize_str(mapped.get("category", ""))
                    category_id = None
                    if cat_name_raw:
                        cat_name = _normalize_category(cat_name_raw)
                        cat_key = cat_name.lower()
                        if cat_key in category_cache:
                            category_id = category_cache[cat_key]
                        else:
                            # Case-insensitive lookup
                            from sqlalchemy import func as sqlfunc
                            existing_cat = (
                                db.query(Category)
                                .filter(sqlfunc.lower(Category.name) == cat_key)
                                .first()
                            )
                            if existing_cat:
                                category_id = existing_cat.id
                            else:
                                new_cat = Category(name=cat_name)
                                db.add(new_cat)
                                db.flush()
                                category_id = new_cat.id
                            category_cache[cat_key] = category_id

                    # ─── Product upsert ────────────────────────
                    # 1. Try by SKU
                    product = None
                    if sku_raw:
                        product = db.query(Product).filter(Product.sku == sku_raw).first()

                    # 2. Try by barcode
                    if product is None and barcode:
                        product = db.query(Product).filter(Product.barcode == barcode).first()

                    if product:
                        # UPDATE all fields
                        product.name = name
                        if sku_raw:
                            product.sku = sku_raw
                        if barcode:
                            product.barcode = barcode
                        product.purchase_price = purchase_price
                        product.sale_price = sale_price
                        product.unit = unit
                        product.category_id = category_id
                        updated += 1
                    else:
                        # CREATE
                        product = Product(
                            name=name,
                            sku=sku,
                            barcode=barcode,
                            purchase_price=purchase_price,
                            sale_price=sale_price,
                            unit=unit,
                            category_id=category_id,
                        )
                        db.add(product)
                        db.flush()
                        imported += 1

                    # ─── Inventory snapshot upsert ─────────────
                    # Key: product_id + warehouse_id → SET (not ADD)
                    existing_inv = (
                        db.query(Inventory)
                        .filter(
                            Inventory.product_id == product.id,
                            Inventory.warehouse_id == warehouse_id,
                        )
                        .first()
                    )
                    if existing_inv:
                        # SNAPSHOT: replace quantity
                        existing_inv.quantity = qty
                    else:
                        db.add(Inventory(
                            product_id=product.id,
                            warehouse_id=warehouse_id,
                            quantity=qty,
                        ))

                except Exception as row_err:
                    errors.append({
                        "row": idx,
                        "error": str(row_err)[:200],
                    })
                    # Continue processing next rows
                    continue

            db.commit()
            return {
                "success": True,
                "products_imported": imported,
                "products_updated": updated,
                "errors": errors[:50],
                "error_count": len(errors),
                "message": (
                    f"Импортировано: {imported}, обновлено: {updated}"
                    + (f", ошибок: {len(errors)}" if errors else "")
                ),
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "message": f"Критическая ошибка: {str(e)}"}
        finally:
            db.close()


class CSVConnector(DataConnector):
    def get_name(self) -> str:
        return "CSV"

    def get_type(self) -> str:
        return "file"

    def get_status(self) -> str:
        return "not_connected"

    async def connect(self, config: Optional[Dict] = None) -> bool:
        return True

    async def validate(self, data: Any) -> Dict[str, Any]:
        """Validate CSV data."""
        try:
            text = self._decode_csv(data)
            reader = csv.DictReader(io.StringIO(text))
            headers = [_normalize_str(h) for h in (reader.fieldnames or [])]
            mapping = _build_mapping(headers, {})

            rows = list(reader)
            valid = sum(
                1 for r in rows
                if any(_normalize_str(v) for v in r.values())
            )
            preview = [
                {_normalize_str(k): _normalize_str(v) for k, v in row.items()}
                for row in rows[:10]
            ]

            return {
                "valid": True,
                "columns_detected": headers,
                "column_mapping": mapping,
                "total_rows": len(rows),
                "valid_rows": valid,
                "error_rows": len(rows) - valid,
                "errors": [],
                "preview_data": preview,
            }
        except Exception as e:
            return {"valid": False, "message": f"Ошибка чтения CSV: {str(e)}"}

    async def import_data(
        self,
        file_data: bytes = None,
        mapping: Dict = None,
        warehouse_id: int = 1,
        **kwargs,
    ) -> Dict:
        """Import from CSV using same logic as Excel."""
        if not file_data:
            return {"success": False, "message": "Файл не предоставлен."}

        try:
            text = self._decode_csv(file_data)
            reader = csv.DictReader(io.StringIO(text))
            headers = [_normalize_str(h) for h in (reader.fieldnames or [])]
            rows = [
                tuple(_normalize_str(row.get(h, "")) for h in reader.fieldnames or [])
                for row in csv.DictReader(io.StringIO(text))
            ]
            excel = ExcelConnector()
            return excel._process_rows(headers, rows, mapping or {}, warehouse_id)
        except Exception as e:
            return {"success": False, "message": f"Ошибка CSV: {str(e)}"}

    def _decode_csv(self, data: bytes) -> str:
        """Try multiple encodings for CSV files."""
        for enc in ("utf-8-sig", "utf-8", "cp1251", "latin-1"):
            try:
                return data.decode(enc)
            except UnicodeDecodeError:
                continue
        raise ValueError("Не удалось декодировать CSV файл")
