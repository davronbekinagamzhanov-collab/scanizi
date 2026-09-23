'use client';
import { useState } from 'react';
import { scannerLookup } from '@/lib/api';
import { formatCurrency, formatNumber } from '@/lib/utils';
import { ScanBarcode, Search, Package } from 'lucide-react';

export default function ScannerPage() {
  const [code, setCode] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const handleSearch = async (e) => {
    e?.preventDefault();
    if (!code.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const res = await scannerLookup(code.trim());
      setResult(res);
    } catch {
      setResult({ found: false, message: 'Ошибка поиска' });
    }
    setLoading(false);
  };

  return (
    <>
      <div className="page-header">
        <div className="page-title-group">
          <h1 className="page-title">Сканер</h1>
          <p className="page-subtitle">Поиск товара по штрихкоду или артикулу</p>
        </div>
      </div>
      <div className="page-content">
        <form onSubmit={handleSearch} style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem', maxWidth: 500 }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <ScanBarcode size={18} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input className="input" placeholder="Введите штрихкод или артикул" value={code} onChange={e => setCode(e.target.value)} style={{ paddingLeft: 40 }} autoFocus />
          </div>
          <button type="submit" className="btn btn-primary" disabled={loading}><Search size={16} /> Найти</button>
        </form>

        {loading && <div className="loading-page" style={{ minHeight: '30vh' }}><div className="spinner" /></div>}

        {searched && !loading && result && (
          result.found ? (
            <div className="card" style={{ maxWidth: 600 }}>
              <h3 style={{ marginBottom: '1rem' }}>{result.product.name}</h3>
              <div style={{ display: 'grid', gap: '0.375rem', fontSize: '0.875rem', marginBottom: '1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}><span className="text-muted">Артикул</span><span style={{ fontFamily: 'monospace' }}>{result.product.sku}</span></div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}><span className="text-muted">Штрихкод</span><span style={{ fontFamily: 'monospace' }}>{result.product.barcode || '—'}</span></div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}><span className="text-muted">Категория</span><span>{result.product.category || '—'}</span></div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}><span className="text-muted">Цена продажи</span><span style={{ fontWeight: 600 }}>{formatCurrency(result.product.sale_price)}</span></div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}><span className="text-muted">Общий остаток</span><span style={{ fontWeight: 700, color: 'var(--accent-400)' }}>{formatNumber(result.total_quantity)} шт.</span></div>
              </div>
              {result.inventory.length > 0 && (
                <>
                  <div className="card-title" style={{ marginBottom: '0.5rem' }}>Остатки по складам</div>
                  <div className="table-container">
                    <table>
                      <thead><tr><th>Магазин</th><th>Склад</th><th>Количество</th></tr></thead>
                      <tbody>
                        {result.inventory.map((inv, i) => (<tr key={i}><td>{inv.store}</td><td>{inv.warehouse}</td><td style={{ fontWeight: 600 }}>{formatNumber(inv.quantity)} шт.</td></tr>))}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
            </div>
          ) : (
            <div className="empty-state">
              <Package size={48} />
              <h3>Товар не найден</h3>
              <p className="text-muted">{result.message}</p>
            </div>
          )
        )}
      </div>
    </>
  );
}
