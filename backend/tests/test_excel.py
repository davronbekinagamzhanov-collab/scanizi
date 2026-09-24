import pytest
import io
try:
    import pandas as pd
except ImportError:
    pd = None

from app.connectors.excel import ExcelConnector, CSVConnector
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Product, Inventory, Category

@pytest.fixture
def sample_excel_bytes():
    if not pd:
        pytest.skip("Pandas not installed")
    df = pd.DataFrame({
        "name": ["Товар 1", "Товар 2", ""],
        "sku": ["SKU-1", "SKU-2", "SKU-3"],
        "barcode": ["111", "222", "333"],
        "purchase_price": ["1000", "2000", "3000"],
        "sale_price": ["1500", "2500", "3500"],
        "quantity": ["10", "20", "30"],
        "category": ["Категория 1", "Категория 2", "Категория 3"],
        "unit": ["шт", "шт", "шт"]
    })
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

@pytest.mark.asyncio
async def test_excel_connector_import(db_session: AsyncSession, sample_excel_bytes):
    connector = ExcelConnector()
    result = await connector.import_data(file_data=sample_excel_bytes, warehouse_id=1, db=db_session)
    
    assert result["success"] is True
    assert result["products_imported"] == 2  # One row is missing name
    assert result["error_count"] == 1
    
@pytest.mark.asyncio
async def test_excel_snapshot_inventory(db_session: AsyncSession, sample_excel_bytes):
    connector = ExcelConnector()
    # First import
    await connector.import_data(file_data=sample_excel_bytes, warehouse_id=1, db=db_session)
    
    # Second import with same file, should update inventory not add
    result = await connector.import_data(file_data=sample_excel_bytes, warehouse_id=1, db=db_session)
    
    assert result["success"] is True
    assert result["products_updated"] == 2
    assert result["products_imported"] == 0
