'use client';
import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { scannerLookup, recordSale, recordPurchase } from '@/lib/api';
import { formatCurrency, formatNumber } from '@/lib/utils';
import { Search, ShoppingCart, Download, Check, AlertCircle } from 'lucide-react';

export default function Operations({ onUpdate }) {
  const searchParams = useSearchParams();
  const initCode = searchParams.get('code') || '';

  const [search, setSearch] = useState(initCode);
  const [product, setProduct] = useState(null);
  const [inventory, setInventory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const [quantity, setQuantity] = useState(1);
  const [price, setPrice] = useState('');
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [warehouseId, setWarehouseId] = useState('');
  const [mode, setMode] = useState(searchParams.get('mode') === 'purchase' ? 'purchase' : 'sale'); // 'sale' | 'purchase'
  const [supplier, setSupplier] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    if (initCode) {
      performSearch(initCode);
    }
  }, [initCode]);

  const performSearch = async (term) => {
    if (!term.trim()) return;
    setLoading(true);
    setError('');
    setProduct(null);
    setSuccess('');
    try {
      const res = await scannerLookup(term);
      if (res.found) {
        setProduct(res.product);
        setInventory(res.inventory || []);
        if (res.inventory?.length > 0) {
            setWarehouseId(res.inventory[0].warehouse_id);
        }
        setPrice(mode === 'sale' ? res.product.sale_price : res.product.purchase_price);
      } else {
        setError('Товар не найден');
      }
    } catch (err) {
      setError(err.message || 'Ошибка поиска');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    performSearch(search);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!product || !warehouseId || quantity <= 0) return;
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      const payload = {
        product_id: product.id,
        warehouse_id: parseInt(warehouseId),
        quantity: parseFloat(quantity),
      };
      
      if (mode === 'sale') {
        payload.unit_price = parseFloat(price) || 0;
        payload.sale_date = date;
        const res = await recordSale(payload);
        setSuccess(res.message || 'Продажа успешна');
      } else {
        payload.unit_cost = parseFloat(price) || 0;
        payload.purchase_date = date;
        payload.supplier = supplier;
        const res = await recordPurchase(payload);
        setSuccess(res.message || 'Приход успешен');
      }
      
      // Reset form partially
      setQuantity(1);
      if (onUpdate) onUpdate();
      
      // Update local inventory mock to reflect immediately
      setInventory(inv => inv.map(i => i.warehouse_id == warehouseId ? { ...i, quantity: mode === 'sale' ? i.quantity - payload.quantity : i.quantity + payload.quantity } : i));
      
    } catch (err) {
      setError(err.message || 'Ошибка операции');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card" style={{ marginBottom: '1.5rem' }}>
      <div className="card-header">
        <span className="card-title">Операции</span>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button 
            className={`btn btn-sm ${mode === 'sale' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => { setMode('sale'); setPrice(product?.sale_price || ''); }}
          >
            Продажа
          </button>
          <button 
            className={`btn btn-sm ${mode === 'purchase' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => { setMode('purchase'); setPrice(product?.purchase_price || ''); }}
          >
            Приход
          </button>
        </div>
      </div>
      
      <div className="card-body">
        <form onSubmit={handleSearch} style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
          <input 
            className="input" 
            placeholder="Поиск по названию, SKU или штрихкоду..." 
            value={search} 
            onChange={e => setSearch(e.target.value)}
            style={{ flex: 1 }}
          />
          <button type="submit" className="btn btn-secondary" disabled={loading}>
            <Search size={16} /> Найти
          </button>
        </form>

        {error && (
          <div style={{ color: 'var(--danger-400)', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertCircle size={16} /> {error}
          </div>
        )}
        
        {success && (
          <div style={{ color: 'var(--accent-400)', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Check size={16} /> {success}
          </div>
        )}

        {product && (
          <div style={{ background: 'var(--bg-secondary)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
              <div>
                <h3 style={{ margin: '0 0 4px', fontSize: '16px' }}>{product.name}</h3>
                <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                  SKU: {product.sku} | Штрихкод: {product.barcode || '—'}
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Текущий остаток</div>
                <div style={{ fontSize: '16px', fontWeight: 'bold', color: 'var(--accent-400)' }}>
                  {formatNumber(inventory.reduce((sum, i) => sum + i.quantity, 0))} шт.
                </div>
              </div>
            </div>

            <form onSubmit={handleSubmit} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '16px', alignItems: 'end' }}>
              <div>
                <label className="text-muted" style={{ fontSize: '12px', display: 'block', marginBottom: '4px' }}>Склад</label>
                <select className="input" value={warehouseId} onChange={e => setWarehouseId(e.target.value)} required>
                  <option value="">Выберите склад...</option>
                  {inventory.map(i => (
                    <option key={i.warehouse_id} value={i.warehouse_id}>
                      {i.warehouse} ({i.quantity} шт.)
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-muted" style={{ fontSize: '12px', display: 'block', marginBottom: '4px' }}>Количество</label>
                <input type="number" min="0.01" step="0.01" className="input" value={quantity} onChange={e => setQuantity(e.target.value)} required />
              </div>
              <div>
                <label className="text-muted" style={{ fontSize: '12px', display: 'block', marginBottom: '4px' }}>Цена</label>
                <input type="number" min="0" step="0.01" className="input" value={price} onChange={e => setPrice(e.target.value)} />
              </div>
              <div>
                <label className="text-muted" style={{ fontSize: '12px', display: 'block', marginBottom: '4px' }}>Дата</label>
                <input type="date" className="input" value={date} onChange={e => setDate(e.target.value)} required max={new Date().toISOString().split('T')[0]} />
              </div>
              
              {mode === 'purchase' && (
                <div>
                  <label className="text-muted" style={{ fontSize: '12px', display: 'block', marginBottom: '4px' }}>Поставщик (опц.)</label>
                  <input type="text" className="input" value={supplier} onChange={e => setSupplier(e.target.value)} />
                </div>
              )}
              
              <div style={{ gridColumn: '1 / -1', display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '8px' }}>
                <div style={{ fontSize: '16px' }}>
                  Итого: <strong style={{ color: 'var(--text-primary)' }}>{formatCurrency((parseFloat(quantity) || 0) * (parseFloat(price) || 0))}</strong>
                </div>
                <button type="submit" className={`btn ${mode === 'sale' ? 'btn-primary' : 'btn-success'}`} disabled={loading || !warehouseId}>
                  {mode === 'sale' ? <><ShoppingCart size={16} /> Продать</> : <><Download size={16} /> Принять на склад</>}
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
