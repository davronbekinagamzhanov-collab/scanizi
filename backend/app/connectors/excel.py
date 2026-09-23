"""
ScanIZI — Excel/CSV Import Connector
Real import with column detection, mapping, validation.
"""

import io
import csv
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from app.connectors.base import DataConnector
from app.models import Product, Category, Inventory, DataSource
from app.db.database import SyncSessionLocal


# Standard column mapping suggestions
COLUMN_MAPPING = {
    "название": "name", "наименование": "name", "товар": "name", "name": "name",
    "артикул": "sku", "sku": "sku", "код": "sku", "code": "sku",
    "штрихкод": "barcode", "barcode": "barcode", "штрих-код": "barcode", "ean": "barcode",
    "цена_закупки": "purchase_price", "закупочная": "purchase_price", "себестоимость": "purchase_price",
    "purchase_price": "purchase_price", "cost": "purchase_price",
    "цена_продажи": "sale_price", "цена": "sale_price", "розничная": "sale_price",
    "sale_price": "sale_price", "price": "sale_price",
    "количество": "quantity", "остаток": "quantity", "кол-во": "quantity",
    "quantity": "quantity", "stock": "quantity", "qty": "quantity",
    "категория": "category", "category": "category", "группа": "category",
    "единица": "unit", "ед.": "unit", "unit": "unit",
}


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
            wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True)
            ws = wb.active

            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                return {"valid": False, "message": "Файл пустой."}

            headers = [str(h).strip().lower() if h else "" for h in rows[0]]

            # Auto-detect column mapping
            mapping = {}
            for i, header in enumerate(headers):
                for pattern, field in COLUMN_MAPPING.items():
                    if pattern in header:
                        mapping[header] = field
                        break

            # Validate rows
            data_rows = rows[1:]
            valid_rows = 0
            errors = []

            for idx, row in enumerate(data_rows[:1000], start=2):
                row_data = dict(zip(headers, row))
                name_col = next((h for h, f in mapping.items() if f == "name"), None)
                if name_col and row_data.get(name_col):
                    valid_rows += 1
                else:
                    errors.append({"row": idx, "error": "Отсутствует название товара"})

            # Preview first 10 rows
            preview = []
            for row in data_rows[:10]:
                preview.append(dict(zip(headers, [str(v) if v else "" for v in row])))

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

    async def import_data(self, file_data: bytes = None, mapping: Dict = None, warehouse_id: int = 1, **kwargs) -> Dict[str, Any]:
        """Import products from Excel file."""
        if not file_data:
            return {"success": False, "message": "Файл не предоставлен."}

        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(file_data), read_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))

            if not rows:
                return {"success": False, "message": "Файл пустой."}

            headers = [str(h).strip().lower() if h else "" for h in rows[0]]
            return self._process_rows(headers, rows[1:], mapping or {}, warehouse_id)

        except Exception as e:
            return {"success": False, "message": f"Ошибка импорта: {str(e)}"}

    def _process_rows(self, headers, data_rows, mapping, warehouse_id):
        """Process imported rows and insert into database."""
        db = SyncSessionLocal()
        imported = 0
        updated = 0
        errors = []

        try:
            for idx, row in enumerate(data_rows, start=2):
                row_data = dict(zip(headers, row))

                # Map columns
                mapped = {}
                for header, value in row_data.items():
                    field = mapping.get(header, COLUMN_MAPPING.get(header.lower()))
                    if field and value is not None:
                        mapped[field] = value

                name = str(mapped.get("name", "")).strip()
                if not name:
                    errors.append({"row": idx, "error": "Пропущено название"})
                    continue

                sku = str(mapped.get("sku", f"IMP-{idx:05d}")).strip()

                # Check existing
                existing = db.query(Product).filter(Product.sku == sku).first()
                if existing:
                    # Update
                    if "purchase_price" in mapped:
                        existing.purchase_price = float(mapped["purchase_price"])
                    if "sale_price" in mapped:
                        existing.sale_price = float(mapped["sale_price"])
                    updated += 1
                else:
                    # Create new
                    product = Product(
                        name=name,
                        sku=sku,
                        barcode=str(mapped.get("barcode", "")).strip() or None,
                        purchase_price=float(mapped.get("purchase_price", 0)),
                        sale_price=float(mapped.get("sale_price", 0)),
                        unit=str(mapped.get("unit", "шт.")),
                    )

                    # Handle category
                    cat_name = str(mapped.get("category", "")).strip()
                    if cat_name:
                        cat = db.query(Category).filter(Category.name == cat_name).first()
                        if not cat:
                            cat = Category(name=cat_name)
                            db.add(cat)
                            db.flush()
                        product.category_id = cat.id

                    db.add(product)
                    db.flush()

                    # Add inventory
                    qty = float(mapped.get("quantity", 0))
                    if qty > 0:
                        db.add(Inventory(
                            product_id=product.id,
                            warehouse_id=warehouse_id,
                            quantity=qty,
                        ))

                    imported += 1

            db.commit()
            return {
                "success": True,
                "products_imported": imported,
                "products_updated": updated,
                "errors": errors[:50],
                "message": f"Импортировано: {imported}, обновлено: {updated}",
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "message": f"Ошибка: {str(e)}"}
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
            text = data.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            headers = [h.strip().lower() for h in (reader.fieldnames or [])]

            mapping = {}
            for header in headers:
                for pattern, field in COLUMN_MAPPING.items():
                    if pattern in header:
                        mapping[header] = field
                        break

            rows = list(reader)
            valid = sum(1 for r in rows if any(r.values()))

            preview = [{k.strip().lower(): v for k, v in row.items()} for row in rows[:10]]

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

    async def import_data(self, file_data: bytes = None, mapping: Dict = None, warehouse_id: int = 1, **kwargs) -> Dict:
        """Import from CSV using the same logic as Excel."""
        if not file_data:
            return {"success": False, "message": "Файл не предоставлен."}

        try:
            text = file_data.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            headers = [h.strip().lower() for h in (reader.fieldnames or [])]
            rows = [tuple(row.get(h, "") for h in reader.fieldnames) for row in csv.DictReader(io.StringIO(text))]

            excel_connector = ExcelConnector()
            return excel_connector._process_rows(headers, rows, mapping or {}, warehouse_id)
        except Exception as e:
            return {"success": False, "message": f"Ошибка: {str(e)}"}
