"""
ScanIZI — DemoDataConnector
Generates realistic demo data: 2 stores, 3 warehouses, ~2000 products, 12 months of sales.
Includes specific scenarios A-F from the spec.
"""

import random
import math
from datetime import date, timedelta, datetime, timezone
from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Session

from app.connectors.base import DataConnector
from app.models import (
    User, Store, Warehouse, Category, Product, Inventory, Sale, DataSource
)
from app.auth.password import hash_password
from app.db.database import SyncSessionLocal


# ─── Product catalog templates ─────────────────────────────────
CATEGORIES_PRODUCTS = {
    "Электроинструменты": [
        ("Дрель ударная", 15000, 22500), ("Шуруповёрт аккумуляторный", 18000, 27900),
        ("Перфоратор SDS-Plus", 25000, 38500), ("Болгарка 125мм", 8000, 12900),
        ("Лобзик электрический", 7500, 11900), ("Фрезер ручной", 22000, 33900),
        ("Циркулярная пила", 19000, 29500), ("Шлифмашина вибрационная", 6500, 9900),
        ("Строительный фен", 5500, 8500), ("Электрорубанок", 12000, 18500),
        ("Миксер строительный", 9000, 13900), ("Рейсмус настольный", 45000, 67500),
        ("Торцовочная пила", 35000, 52900), ("Пылесос строительный", 14000, 21500),
        ("Компрессор поршневой", 28000, 42900), ("Генератор бензиновый", 55000, 82500),
        ("Сварочный аппарат инверторный", 15000, 23500), ("Краскопульт электрический", 8500, 13200),
        ("Гравер электрический", 4500, 6900), ("Точило электрическое", 6000, 9200),
    ],
    "Ручной инструмент": [
        ("Набор отвёрток", 1500, 2900), ("Молоток слесарный 500г", 800, 1500),
        ("Плоскогубцы 200мм", 900, 1700), ("Ключ разводной 250мм", 1200, 2200),
        ("Набор гаечных ключей", 3500, 5900), ("Уровень пузырьковый 600мм", 1800, 3200),
        ("Рулетка 5м", 600, 1100), ("Ножовка по дереву", 1200, 2100),
        ("Набор бит", 800, 1500), ("Стамеска 20мм", 500, 950),
        ("Струбцина F-образная", 1500, 2700), ("Пассатижи 180мм", 700, 1300),
        ("Ножницы по металлу", 1100, 1900), ("Клещи переставные", 1600, 2800),
        ("Набор шестигранников", 900, 1600), ("Напильник плоский", 400, 750),
        ("Кусачки боковые", 650, 1200), ("Топор плотницкий", 2200, 3800),
        ("Монтировка 600мм", 800, 1400), ("Зубило 250мм", 350, 650),
    ],
    "Строительные материалы": [
        ("Цемент М400 50кг", 1800, 2500), ("Гипсокартон 2500x1200x12.5мм", 900, 1500),
        ("Штукатурка гипсовая 30кг", 1200, 1900), ("Шпатлёвка финишная 20кг", 1500, 2400),
        ("Грунтовка универсальная 10л", 2800, 4200), ("Плиточный клей 25кг", 800, 1300),
        ("Затирка для швов 2кг", 600, 1100), ("Пена монтажная 750мл", 350, 650),
        ("Герметик силиконовый 280мл", 250, 450), ("Клей ПВА строительный 10кг", 1800, 2900),
        ("Сетка армирующая 1x50м", 2500, 3900), ("Утеплитель минвата 50мм", 3200, 4800),
        ("Пенопласт 50мм 1x1м", 800, 1300), ("Гидроизоляция обмазочная 10кг", 3500, 5400),
        ("Профиль ПН 28x27 3м", 180, 350), ("Профиль ПС 60x27 3м", 250, 450),
        ("Подвес прямой", 15, 35), ("Саморезы для ГКЛ 3.5x25 1000шт", 400, 700),
        ("Лента серпянка 45мм 90м", 200, 380), ("Уголок перфорированный 3м", 120, 250),
    ],
    "Садовые товары": [
        ("Газонокосилка электрическая", 18000, 27900), ("Триммер бензиновый", 12000, 18500),
        ("Секатор садовый", 800, 1500), ("Лопата штыковая", 1200, 2100),
        ("Грабли веерные", 600, 1100), ("Шланг поливочный 20м", 2500, 3900),
        ("Распылитель садовый", 350, 650), ("Тачка садовая 80л", 5500, 8500),
        ("Опрыскиватель 5л", 1800, 2900), ("Бензопила цепная", 22000, 33900),
        ("Кусторез электрический", 8000, 12500), ("Садовые ножницы", 1500, 2600),
        ("Вилы садовые", 1100, 1900), ("Мотыга", 500, 900),
        ("Лейка 10л", 400, 750), ("Перчатки садовые", 200, 400),
    ],
    "Лестницы": [
        ("Стремянка алюм. 4 ступени", 5500, 8500), ("Стремянка алюм. 6 ступеней", 8000, 12500),
        ("Стремянка алюм. 8 ступеней", 12000, 18500), ("Лестница трёхсекционная 3x8", 25000, 38500),
        ("Лестница трёхсекционная 3x12", 42000, 63900), ("Лестница-трансформер 4x4", 28000, 42900),
        ("Стремянка стальная 5 ступеней", 4500, 6900), ("Подмости малярные", 8500, 13200),
        ("Лестница приставная 10 ступеней", 6000, 9200), ("Стремянка диэлектрическая", 15000, 23500),
    ],
    "Крепёж": [
        ("Саморезы 4x40 500шт", 250, 450), ("Гвозди 3x70 5кг", 600, 1000),
        ("Болты M8x60 100шт", 350, 650), ("Гайки M8 100шт", 150, 300),
        ("Шайбы M8 200шт", 100, 200), ("Анкеры 10x100 50шт", 450, 800),
        ("Дюбель-гвоздь 6x40 200шт", 200, 380), ("Шурупы по дереву 5x50 500шт", 300, 550),
        ("Саморезы кровельные 100шт", 280, 500), ("Винты M6x30 100шт", 180, 350),
        ("Хомуты металлические набор", 250, 450), ("Заклёпки вытяжные 500шт", 350, 600),
        ("Скобы для степлера 1000шт", 150, 280), ("Шпильки M10 1м", 200, 380),
        ("Саморезы для профиля 1000шт", 180, 320), ("Уголок крепёжный 50x50 10шт", 250, 450),
    ],
    "Расходные материалы": [
        ("Диск отрезной 125мм", 120, 250), ("Диск шлифовальный 125мм", 180, 350),
        ("Свёрла по металлу набор", 800, 1500), ("Свёрла по бетону набор", 600, 1100),
        ("Биты для шуруповёрта набор", 500, 900), ("Коронки биметаллические набор", 2500, 3900),
        ("Полотна для лобзика набор", 350, 650), ("Наждачная бумага набор", 200, 380),
        ("Перчатки рабочие 12 пар", 800, 1400), ("Очки защитные", 300, 550),
        ("Респиратор", 150, 300), ("Изолента 19мм 20м", 80, 150),
        ("Скотч малярный 48мм 50м", 120, 220), ("Плёнка укрывная 4x5м", 200, 380),
        ("Мешки строительные 50шт", 300, 550), ("Кисть малярная 100мм", 150, 280),
        ("Валик малярный 250мм", 250, 450), ("Шпатель 150мм", 120, 220),
        ("Ведро строительное 20л", 250, 450), ("Лезвия для ножа 18мм 10шт", 100, 200),
    ],
    "Товары для дома": [
        ("Смеситель для кухни", 5500, 8500), ("Смеситель для ванны", 7500, 11900),
        ("Унитаз компакт", 12000, 18500), ("Раковина накладная", 4500, 6900),
        ("Ванна акриловая 150см", 25000, 38500), ("Душевая стойка", 8000, 12500),
        ("Полотенцесушитель", 6000, 9200), ("Сифон для раковины", 500, 900),
        ("Гибкая подводка 1/2 80см", 200, 380), ("Кран шаровый 1/2", 350, 650),
        ("Фильтр для воды", 3500, 5400), ("Водонагреватель 50л", 18000, 27900),
        ("Вентилятор вытяжной", 2500, 3900), ("Зеркало для ванной", 4000, 6200),
        ("Карниз для шторы", 1500, 2600),
    ],
    "Электрика": [
        ("Кабель ВВГнг 3x2.5 50м", 4500, 6900), ("Кабель ВВГнг 3x1.5 50м", 3000, 4800),
        ("Автомат 16А", 350, 650), ("Автомат 25А", 400, 750),
        ("УЗО 25А 30мА", 1800, 2900), ("Розетка двойная с заземлением", 250, 450),
        ("Выключатель одноклавишный", 150, 300), ("Выключатель двухклавишный", 200, 380),
        ("Щиток на 12 модулей", 2500, 3900), ("Гофра ПВХ 20мм 50м", 600, 1000),
        ("Клеммы WAGO 5-пров. 10шт", 350, 600), ("Лампа LED E27 10Вт", 200, 380),
        ("Светильник потолочный LED", 3500, 5400), ("Удлинитель 3м 4 розетки", 800, 1400),
        ("Счётчик электрический 1-фазный", 3000, 4800),
    ],
}


class DemoDataConnector(DataConnector):
    """Generates realistic demo data with predefined analytical scenarios."""

    def get_name(self) -> str:
        return "Демо-данные"

    def get_type(self) -> str:
        return "manual"

    def get_status(self) -> str:
        return "demo"

    async def connect(self, config: Optional[Dict] = None) -> bool:
        return True

    async def validate(self, data: Any) -> Dict[str, Any]:
        return {"valid": True}

    async def import_data(self, **kwargs) -> Dict[str, Any]:
        """Generate and insert all demo data synchronously."""
        db = SyncSessionLocal()
        try:
            return self._seed_all(db)
        finally:
            db.close()

    def _seed_all(self, db: Session) -> Dict[str, Any]:
        random.seed(42)  # Reproducible

        # ─── Users ──────────────────────────────────
        users = [
            User(
                username="admin", password_hash=hash_password("admin"),
                full_name="Давронбек Инагамжанов", role="owner"
            ),
            User(
                username="manager", password_hash=hash_password("manager"),
                full_name="Алишер Мак Камжанов", role="manager"
            ),
            User(
                username="employee", password_hash=hash_password("employee"),
                full_name="Ерлан Касымов", role="employee"
            ),
        ]
        db.add_all(users)
        db.flush()

        # ─── Stores ─────────────────────────────────
        store1 = Store(name="Мастер Плюс Центр", address="ул. Абая 15, Алматы")
        store2 = Store(name="Мастер Плюс Юг", address="ул. Толе Би 120, Алматы")
        db.add_all([store1, store2])
        db.flush()

        # Assign users to store
        users[1].store_id = store1.id
        users[2].store_id = store1.id

        # ─── Warehouses ─────────────────────────────
        wh1 = Warehouse(name="Основной склад Центр", store_id=store1.id, address="ул. Абая 15")
        wh2 = Warehouse(name="Основной склад Юг", store_id=store2.id, address="ул. Толе Би 120")
        wh3 = Warehouse(name="Резервный склад", store_id=store1.id, address="ул. Сейфуллина 200")
        db.add_all([wh1, wh2, wh3])
        db.flush()

        # ─── Categories ─────────────────────────────
        categories = {}
        for cat_name in CATEGORIES_PRODUCTS:
            cat = Category(name=cat_name)
            db.add(cat)
            db.flush()
            categories[cat_name] = cat

        # ─── Products ───────────────────────────────
        products = []
        product_id = 0
        today = date.today()

        for cat_name, items in CATEGORIES_PRODUCTS.items():
            cat = categories[cat_name]

            # Generate multiple variants of each product to reach ~2000
            variants_per_item = max(1, 2000 // sum(len(v) for v in CATEGORIES_PRODUCTS.values()))

            for item_name, buy_price, sell_price in items:
                for variant in range(variants_per_item + 1):
                    product_id += 1
                    if variant == 0:
                        name = item_name
                    else:
                        suffixes = ["Pro", "Lite", "Стандарт", "Премиум", "Мини", "Макс", "XL", "Эконом"]
                        suffix = suffixes[variant % len(suffixes)]
                        name = f"{item_name} {suffix}"
                        buy_price_v = buy_price * (0.7 + random.random() * 0.6)
                        sell_price_v = buy_price_v * (1.3 + random.random() * 0.5)
                        buy_price = round(buy_price_v, -1)
                        sell_price = round(sell_price_v, -1)

                    sku = f"SKU-{cat_name[:3].upper()}-{product_id:05d}"
                    barcode = f"48000{product_id:08d}"

                    # Seasonal flags for garden products
                    is_seasonal = cat_name == "Садовые товары"
                    season_months = "4,5,6,7,8,9" if is_seasonal else None

                    product = Product(
                        name=name, sku=sku, barcode=barcode,
                        category_id=cat.id,
                        purchase_price=buy_price, sale_price=sell_price,
                        unit="шт.",
                        is_seasonal=is_seasonal,
                        season_months=season_months,
                    )
                    db.add(product)
                    db.flush()
                    products.append(product)

                    if len(products) >= 2000:
                        break
                if len(products) >= 2000:
                    break

        # ─── Inventory + Sales ───────────────────────
        # Generate inventory and 12 months of sales with specific scenarios
        scenario_products = self._assign_scenarios(products)
        total_sales = 0

        for product in products:
            scenario = scenario_products.get(product.id, "C")  # Default: normal
            inv_qty1, inv_qty2, inv_qty3, sales_pattern = self._get_scenario_params(
                scenario, product.purchase_price, product.sale_price
            )

            # Inventory
            db.add(Inventory(product_id=product.id, warehouse_id=wh1.id, quantity=inv_qty1))
            db.add(Inventory(product_id=product.id, warehouse_id=wh2.id, quantity=inv_qty2))
            if inv_qty3 > 0:
                db.add(Inventory(product_id=product.id, warehouse_id=wh3.id, quantity=inv_qty3))

            # Sales: 12 months of history
            for day_offset in range(90):
                sale_date = today - timedelta(days=day_offset)
                month = sale_date.month

                # Base daily sales from pattern
                base_sales = sales_pattern(day_offset, month)
                if base_sales <= 0:
                    continue

                # Add some randomness
                actual_sales = max(0, int(base_sales + random.gauss(0, base_sales * 0.3)))
                if actual_sales == 0:
                    continue

                # Split between stores
                store1_share = random.uniform(0.3, 0.7)
                s1_qty = max(0, int(actual_sales * store1_share))
                s2_qty = max(0, actual_sales - s1_qty)

                if s1_qty > 0:
                    db.add(Sale(
                        product_id=product.id, store_id=store1.id,
                        quantity=s1_qty, unit_price=product.sale_price,
                        total_price=s1_qty * product.sale_price,
                        sale_date=sale_date,
                    ))
                    total_sales += 1

                if s2_qty > 0:
                    db.add(Sale(
                        product_id=product.id, store_id=store2.id,
                        quantity=s2_qty, unit_price=product.sale_price,
                        total_price=s2_qty * product.sale_price,
                        sale_date=sale_date,
                    ))
                    total_sales += 1

            # Commit in batches
            if product.id % 100 == 0:
                db.commit()

        # ─── Data Sources ──────────────────────────
        db.add(DataSource(
            name="Демо-данные", source_type="manual", status="demo",
            records_imported=len(products), last_sync=datetime.now(timezone.utc)
        ))
        db.add(DataSource(name="1С", source_type="api", status="not_connected"))
        db.add(DataSource(name="GBS", source_type="api", status="not_connected"))
        db.add(DataSource(name="Excel", source_type="file", status="not_connected"))
        db.add(DataSource(name="CSV", source_type="file", status="not_connected"))

        db.commit()

        return {
            "success": True,
            "products_imported": len(products),
            "sales_records": total_sales,
            "stores": 2,
            "warehouses": 3,
            "categories": len(categories),
            "message": "Демонстрационные данные загружены успешно.",
        }

    def _assign_scenarios(self, products: list) -> Dict[int, str]:
        """Assign demo scenarios to products."""
        scenarios = {}
        n = len(products)

        # Scenario A: hot seller, low stock (5%)
        for p in products[:int(n * 0.05)]:
            scenarios[p.id] = "A"

        # Scenario B: expensive, almost no sales (5%)
        expensive = sorted(products, key=lambda p: p.purchase_price, reverse=True)
        for p in expensive[:int(n * 0.05)]:
            if p.id not in scenarios:
                scenarios[p.id] = "B"

        # Scenario D: imbalanced stores (3%)
        for p in products[int(n * 0.30):int(n * 0.33)]:
            scenarios[p.id] = "D"

        # Scenario E: seasonal (garden products already flagged)
        for p in products:
            if p.is_seasonal and p.id not in scenarios:
                scenarios[p.id] = "E"

        # Scenario F: demand drop (3%)
        for p in products[int(n * 0.50):int(n * 0.53)]:
            if p.id not in scenarios:
                scenarios[p.id] = "F"

        return scenarios

    def _get_scenario_params(self, scenario: str, buy_price: float, sell_price: float):
        """Return inventory quantities and sales pattern function per scenario."""

        if scenario == "A":
            # Hot seller, almost out of stock
            return (3, 5, 0, lambda day, month: random.uniform(2, 8))

        elif scenario == "B":
            # Expensive, dead stock
            return (
                random.randint(30, 80),
                random.randint(20, 50),
                random.randint(10, 30),
                lambda day, month: 0.05 if random.random() < 0.03 else 0
            )

        elif scenario == "D":
            # Imbalanced: store1 has way more than store2
            return (
                120,  # excess in store 1
                8,    # deficit in store 2
                0,
                lambda day, month: random.uniform(0.5, 3)  # Store 2 sells more
            )

        elif scenario == "E":
            # Seasonal: garden products
            def seasonal_sales(day, month):
                if month in [4, 5, 6, 7, 8]:
                    return random.uniform(1, 5)
                elif month in [3, 9]:
                    return random.uniform(0.2, 1)
                else:
                    return 0.05 if random.random() < 0.05 else 0
            return (random.randint(15, 60), random.randint(10, 40), 0, seasonal_sales)

        elif scenario == "F":
            # Demand drop: was selling well, now dropped
            def demand_drop(day, month):
                if day < 30:  # Recent: very low
                    return random.uniform(0, 0.5)
                elif day < 60:  # Declining
                    return random.uniform(0.5, 2)
                else:  # Was fine
                    return random.uniform(2, 6)
            return (random.randint(20, 50), random.randint(15, 35), 0, demand_drop)

        else:
            # Scenario C: Normal product
            base_rate = max(0.1, (sell_price - buy_price) / sell_price * 3)
            return (
                random.randint(10, 80),
                random.randint(5, 40),
                random.randint(0, 15),
                lambda day, month, br=base_rate: random.uniform(br * 0.3, br * 1.5)
            )
