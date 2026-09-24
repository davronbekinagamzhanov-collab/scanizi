"""Inventory Transaction Service — единая логика движения товаров"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from datetime import date

from app.models import Product, Warehouse, Store, Inventory, Sale, Purchase

class InventoryTransactionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _resolve_store(self, warehouse_id: int) -> int:
        wh_r = await self.db.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
        wh = wh_r.scalar_one_or_none()
        if not wh:
            raise HTTPException(status_code=400, detail="Склад не найден")
        return wh.store_id

    async def record_sale(self, data: dict) -> dict:
        product_id = data.get("product_id")
        warehouse_id = data.get("warehouse_id")
        store_id = data.get("store_id")
        quantity = float(data.get("quantity", 0))
        unit_price = data.get("unit_price")  # Can be None
        sale_date_str = data.get("sale_date")

        if not product_id or quantity <= 0:
            raise HTTPException(status_code=400, detail="product_id и quantity (>0) обязательны")
        
        # Validate date
        if sale_date_str:
            sale_date = date.fromisoformat(sale_date_str)
            if sale_date > date.today():
                raise HTTPException(status_code=400, detail="Дата продажи не может быть в будущем")
        else:
            sale_date = date.today()

        # Check product
        prod_r = await self.db.execute(select(Product).where(Product.id == product_id))
        product = prod_r.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Товар не найден")

        # Resolve warehouse & store
        if not warehouse_id:
            # find first warehouse with stock
            inv_r = await self.db.execute(
                select(Inventory).where(Inventory.product_id == product_id)
                .order_by(Inventory.quantity.desc()).limit(1).with_for_update()
            )
        else:
            inv_r = await self.db.execute(
                select(Inventory).where(
                    Inventory.product_id == product_id,
                    Inventory.warehouse_id == warehouse_id
                ).with_for_update()
            )

        inventory = inv_r.scalar_one_or_none()
        if not inventory:
            raise HTTPException(status_code=400, detail="Остатки для данного товара не найдены")

        if not warehouse_id:
            warehouse_id = inventory.warehouse_id

        resolved_store_id = await self._resolve_store(warehouse_id)
        if store_id and store_id != resolved_store_id:
            raise HTTPException(status_code=400, detail="Склад не принадлежит указанному магазину")
        store_id = resolved_store_id

        if inventory.quantity < quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Недостаточно товара: доступно {inventory.quantity}, запрошено {quantity}"
            )

        # Inventory decrement
        inventory.quantity -= quantity

        # Price fallback
        final_price = float(unit_price) if unit_price is not None else product.sale_price

        sale = Sale(
            product_id=product_id,
            store_id=store_id,
            warehouse_id=warehouse_id,
            quantity=quantity,
            unit_price=final_price,
            total_price=final_price * quantity,
            sale_date=sale_date,
        )
        self.db.add(sale)
        await self.db.flush()

        return {
            "success": True,
            "sale_id": sale.id,
            "product": product.name,
            "quantity_sold": quantity,
            "inventory_remaining": inventory.quantity,
            "message": f"Продажа записана. Остаток: {inventory.quantity} шт."
        }

    async def record_purchase(self, data: dict) -> dict:
        product_id = data.get("product_id")
        warehouse_id = data.get("warehouse_id")
        store_id = data.get("store_id")
        quantity = float(data.get("quantity", 0))
        unit_cost = data.get("unit_cost")
        purchase_date_str = data.get("purchase_date")
        supplier = data.get("supplier")

        if not product_id or not warehouse_id or quantity <= 0:
            raise HTTPException(status_code=400, detail="product_id, warehouse_id и quantity (>0) обязательны")

        if purchase_date_str:
            purchase_date = date.fromisoformat(purchase_date_str)
            if purchase_date > date.today():
                raise HTTPException(status_code=400, detail="Дата прихода не может быть в будущем")
        else:
            purchase_date = date.today()

        # Check product
        prod_r = await self.db.execute(select(Product).where(Product.id == product_id))
        product = prod_r.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Товар не найден")

        resolved_store_id = await self._resolve_store(warehouse_id)
        if store_id and store_id != resolved_store_id:
            raise HTTPException(status_code=400, detail="Склад не принадлежит указанному магазину")
        store_id = resolved_store_id

        # Update or create inventory
        inv_r = await self.db.execute(
            select(Inventory).where(
                Inventory.product_id == product_id,
                Inventory.warehouse_id == warehouse_id
            ).with_for_update()
        )
        inventory = inv_r.scalar_one_or_none()

        if inventory:
            inventory.quantity += quantity
        else:
            inventory = Inventory(
                product_id=product_id,
                warehouse_id=warehouse_id,
                quantity=quantity,
                last_updated=purchase_date
            )
            self.db.add(inventory)
            await self.db.flush()

        final_cost = float(unit_cost) if unit_cost is not None else product.purchase_price

        purchase = Purchase(
            product_id=product_id,
            store_id=store_id,
            warehouse_id=warehouse_id,
            quantity=quantity,
            unit_cost=final_cost,
            total_cost=final_cost * quantity,
            purchase_date=purchase_date,
            supplier=supplier,
        )
        self.db.add(purchase)
        await self.db.flush()

        return {
            "success": True,
            "purchase_id": purchase.id,
            "product": product.name,
            "quantity_received": quantity,
            "inventory_remaining": inventory.quantity,
            "message": f"Приход записан. Остаток: {inventory.quantity} шт."
        }
