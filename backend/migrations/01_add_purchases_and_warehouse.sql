-- Idempotent SQL Migration for ScanIZI Production (Supabase/PostgreSQL)
-- Adds the `purchases` table and `warehouse_id` to `sales` safely.

DO $$ 
BEGIN
    -- 1. Create purchases table if not exists
    CREATE TABLE IF NOT EXISTS purchases (
        id SERIAL PRIMARY KEY,
        product_id INTEGER NOT NULL,
        store_id INTEGER NOT NULL,
        warehouse_id INTEGER NOT NULL,
        quantity DOUBLE PRECISION NOT NULL,
        unit_cost DOUBLE PRECISION NOT NULL,
        total_cost DOUBLE PRECISION NOT NULL,
        purchase_date DATE NOT NULL,
        supplier VARCHAR(255),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    -- 2. Add foreign keys safely
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_purchases_product_id') THEN
        ALTER TABLE purchases ADD CONSTRAINT fk_purchases_product_id FOREIGN KEY (product_id) REFERENCES products(id);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_purchases_store_id') THEN
        ALTER TABLE purchases ADD CONSTRAINT fk_purchases_store_id FOREIGN KEY (store_id) REFERENCES stores(id);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_purchases_warehouse_id') THEN
        ALTER TABLE purchases ADD CONSTRAINT fk_purchases_warehouse_id FOREIGN KEY (warehouse_id) REFERENCES warehouses(id);
    END IF;

    -- 3. Create indexes safely
    IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'ix_purchases_product_id') THEN
        CREATE INDEX ix_purchases_product_id ON purchases (product_id);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'ix_purchases_store_id') THEN
        CREATE INDEX ix_purchases_store_id ON purchases (store_id);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'ix_purchases_warehouse_id') THEN
        CREATE INDEX ix_purchases_warehouse_id ON purchases (warehouse_id);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'ix_purchases_purchase_date') THEN
        CREATE INDEX ix_purchases_purchase_date ON purchases (purchase_date);
    END IF;

    -- 4. Add warehouse_id to sales safely
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='sales' AND column_name='warehouse_id') THEN
        ALTER TABLE sales ADD COLUMN warehouse_id INTEGER;
    END IF;

    -- 5. Add foreign key and index to sales.warehouse_id
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_sales_warehouse_id') THEN
        ALTER TABLE sales ADD CONSTRAINT fk_sales_warehouse_id FOREIGN KEY (warehouse_id) REFERENCES warehouses(id);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'ix_sales_warehouse_id') THEN
        CREATE INDEX ix_sales_warehouse_id ON sales (warehouse_id);
    END IF;

END $$;
