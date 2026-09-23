'use client';
import { useState, useEffect } from 'react';
import { getWarehouses, getTransfers } from '@/lib/api';
import { formatNumber, formatCurrency } from '@/lib/utils';
import { Warehouse as WarehouseIcon, ArrowRight } from 'lucide-react';

export default function WarehousesPage() {
  const [warehouses, setWarehouses] = useState([]);
  const [transfers, setTransfers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getWarehouses(), getTransfers().catch(() => [])])
      .then(([wh, tr]) => { setWarehouses(wh); setTransfers(tr); })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading-page"><div className="spinner" /></div>;

  return (
    <>
      <div className="page-header">
        <div className="page-title-group">
          <h1 className="page-title">Склады</h1>
          <p className="page-subtitle">{warehouses.length} складов</p>
        </div>
      </div>
      <div className="page-content">
        <div className="grid-3" style={{ marginBottom: '1.5rem' }}>
          {warehouses.map(wh => (
            <div className="metric-card" key={wh.id}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <WarehouseIcon size={18} style={{ color: 'var(--primary-400)' }} />
                <div className="metric-label" style={{ textTransform: 'none', fontSize: '0.875rem', fontWeight: 600 }}>{wh.name}</div>
              </div>
              <div className="metric-sub">{wh.store_name}</div>
              <div style={{ display: 'flex', gap: '1.5rem', marginTop: '0.5rem' }}>
                <div><span className="text-muted" style={{ fontSize: '0.75rem' }}>Позиций: </span><span style={{ fontWeight: 600 }}>{wh.product_count}</span></div>
                <div><span className="text-muted" style={{ fontSize: '0.75rem' }}>Количество: </span><span style={{ fontWeight: 600 }}>{formatNumber(wh.total_quantity)}</span></div>
              </div>
            </div>
          ))}
        </div>

        {transfers.length > 0 && (
          <div className="card">
            <div className="card-header"><span className="card-title">Предложения по перемещению</span></div>
            <div className="table-container">
              <table>
                <thead><tr><th>Товар</th><th>Откуда</th><th>Кол-во</th><th></th><th>Куда</th><th>Кол-во</th><th>Переместить</th><th>Причина</th></tr></thead>
                <tbody>
                  {transfers.map((t, i) => (
                    <tr key={i}>
                      <td style={{ fontWeight: 500 }}>{t.product_name}</td>
                      <td>{t.from_store}</td>
                      <td>{t.from_quantity}</td>
                      <td><ArrowRight size={14} style={{ color: 'var(--primary-400)' }} /></td>
                      <td>{t.to_store}</td>
                      <td>{t.to_quantity}</td>
                      <td><span className="badge badge-primary">{t.suggested_transfer} шт.</span></td>
                      <td style={{ fontSize: '0.75rem', maxWidth: 300, whiteSpace: 'normal' }}>{t.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
