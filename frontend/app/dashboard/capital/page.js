'use client';
import { useState, useEffect } from 'react';
import { getCapital } from '@/lib/api';
import { formatCurrency, formatNumber, trendBadge } from '@/lib/utils';
import Link from 'next/link';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { DollarSign, AlertTriangle } from 'lucide-react';

export default function CapitalPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCapital().then(setData).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading-page"><div className="spinner" /></div>;
  const d = data || {};

  return (
    <>
      <div className="page-header">
        <div className="page-title-group">
          <h1 className="page-title">Управление капиталом</h1>
          <p className="page-subtitle">Анализ замороженных и неэффективных вложений</p>
        </div>
      </div>
      <div className="page-content">
        <div className="grid-3" style={{ marginBottom: '1.5rem' }}>
          <div className="metric-card"><div className="metric-label">Общий капитал в остатках</div><div className="metric-value">{formatCurrency(d.total_capital)}</div></div>
          <div className="metric-card" style={{ borderColor: 'rgba(244,63,94,0.3)' }}><div className="metric-label">Замороженный капитал</div><div className="metric-value" style={{ color: 'var(--danger-400)' }}>{formatCurrency(d.frozen_capital)}</div><div className="metric-sub">{d.frozen_percent?.toFixed(1)}% от остатков</div></div>
          <div className="metric-card"><div className="metric-label">Эффективный капитал</div><div className="metric-value" style={{ color: 'var(--accent-400)' }}>{formatCurrency((d.total_capital||0) - (d.frozen_capital||0))}</div></div>
        </div>

        <div className="grid-2" style={{ marginBottom: '1.5rem' }}>
          <div className="card">
            <div className="card-header"><span className="card-title">По категориям</span></div>
            <div style={{ height: 250 }}>
              <ResponsiveContainer>
                <BarChart data={d.by_category || []} layout="vertical">
                  <CartesianGrid stroke="rgba(99,102,241,0.06)" />
                  <XAxis type="number" tick={{ fontSize: 10, fill: '#64748b' }} tickFormatter={v => v >= 1000 ? `${(v/1000).toFixed(0)}k` : v} />
                  <YAxis type="category" dataKey="category" tick={{ fontSize: 10, fill: '#94a3b8' }} width={120} />
                  <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(99,102,241,0.2)', borderRadius: 8, fontSize: 12 }} formatter={v => formatCurrency(v)} />
                  <Bar dataKey="value" fill="#f43f5e" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="card">
            <div className="card-header"><span className="card-title">По магазинам</span></div>
            <div style={{ height: 250 }}>
              <ResponsiveContainer>
                <BarChart data={d.by_store || []}>
                  <CartesianGrid stroke="rgba(99,102,241,0.06)" />
                  <XAxis dataKey="store" tick={{ fontSize: 10, fill: '#64748b' }} />
                  <YAxis tick={{ fontSize: 10, fill: '#64748b' }} tickFormatter={v => v >= 1000 ? `${(v/1000).toFixed(0)}k` : v} />
                  <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(99,102,241,0.2)', borderRadius: 8, fontSize: 12 }} formatter={v => formatCurrency(v)} />
                  <Bar dataKey="value" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {d.high_risk_products?.length > 0 && (
          <div className="card">
            <div className="card-header"><span className="card-title"><AlertTriangle size={14} style={{ display: 'inline', marginRight: 6, verticalAlign: -2 }} />Товары с наибольшим замороженным капиталом</span></div>
            <div className="table-container">
              <table>
                <thead><tr><th>Товар</th><th>Стоимость остатка</th><th>Продажи 30д</th><th>Без продаж</th><th>Тренд</th></tr></thead>
                <tbody>
                  {d.high_risk_products.slice(0, 15).map((p, i) => {
                    const tb = trendBadge(p.trend);
                    return (<tr key={i}><td><Link href={`/dashboard/products/${p.product_id}`} style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{p.product_name}</Link></td><td style={{ fontWeight: 600 }}>{formatCurrency(p.inventory_value)}</td><td>{p.sales_30d} шт.</td><td>{p.days_without_sale} дн.</td><td><span className={`badge ${tb.cls}`}>{tb.label}</span></td></tr>);
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
