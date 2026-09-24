'use client';
import { useState, useEffect, Suspense } from 'react';
import { getSalesSummary } from '@/lib/api';
import { formatCurrency, formatNumber } from '@/lib/utils';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, PieChart, Pie, Cell } from 'recharts';
import { TrendingUp, ShoppingCart } from 'lucide-react';

import Operations from './Operations';

const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#f43f5e', '#0ea5e9', '#8b5cf6', '#ec4899', '#14b8a6'];

export default function SalesPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadData = () => {
    getSalesSummary().then(setData).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) return <div className="loading-page"><div className="spinner" /></div>;

  const d = data || {};
  return (
    <>
      <div className="page-header">
        <div className="page-title-group">
          <h1 className="page-title">Продажи и Приходы</h1>
          <p className="page-subtitle">Операции и аналитика выручки</p>
        </div>
      </div>
      <div className="page-content">
        <Suspense fallback={<div>Loading operations...</div>}>
          <Operations onUpdate={loadData} />
        </Suspense>
        
        <div className="grid-4" style={{ marginBottom: '1.5rem' }}>
          <div className="metric-card"><div className="metric-label">Сегодня</div><div className="metric-value">{formatCurrency(d.total_sales_today)}</div></div>
          <div className="metric-card"><div className="metric-label">7 дней</div><div className="metric-value">{formatCurrency(d.total_sales_7d)}</div></div>
          <div className="metric-card"><div className="metric-label">30 дней</div><div className="metric-value">{formatCurrency(d.total_sales_30d)}</div></div>
          <div className="metric-card"><div className="metric-label">90 дней</div><div className="metric-value">{formatCurrency(d.total_sales_90d)}</div></div>
        </div>

        <div className="grid-2" style={{ marginBottom: '1.5rem' }}>
          <div className="card">
            <div className="card-header"><span className="card-title"><ShoppingCart size={14} style={{ display: 'inline', marginRight: 6, verticalAlign: -2 }} />Выручка за 30 дней</span></div>
            <div style={{ width: '100%', height: 260 }}>
              <ResponsiveContainer>
                <AreaChart data={d.daily_sales || []}>
                  <defs><linearGradient id="sg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#6366f1" stopOpacity={0.3} /><stop offset="100%" stopColor="#6366f1" stopOpacity={0} /></linearGradient></defs>
                  <CartesianGrid stroke="rgba(99,102,241,0.06)" />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#64748b' }} tickFormatter={v => v.slice(5)} interval="preserveStartEnd" />
                  <YAxis tick={{ fontSize: 10, fill: '#64748b' }} tickFormatter={v => v >= 1000 ? `${(v/1000).toFixed(0)}k` : v} />
                  <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(99,102,241,0.2)', borderRadius: 8, fontSize: 12 }} formatter={v => [formatCurrency(v), 'Выручка']} />
                  <Area type="monotone" dataKey="total" stroke="#6366f1" fill="url(#sg)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="card">
            <div className="card-header"><span className="card-title">По категориям</span></div>
            <div style={{ width: '100%', height: 260 }}>
              <ResponsiveContainer>
                <PieChart>
                  <Pie data={d.sales_by_category || []} dataKey="revenue" nameKey="category" cx="50%" cy="50%" outerRadius={90} label={({ category, percent }) => `${category?.slice(0,12)} ${(percent*100).toFixed(0)}%`} labelLine={{ stroke: '#64748b' }} style={{ fontSize: 10 }}>
                    {(d.sales_by_category || []).map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(99,102,241,0.2)', borderRadius: 8, fontSize: 12 }} formatter={v => formatCurrency(v)} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {d.top_products?.length > 0 && (
          <div className="card">
            <div className="card-header"><span className="card-title"><TrendingUp size={14} style={{ display: 'inline', marginRight: 6, verticalAlign: -2 }} />ТОП-10 по выручке (30 дней)</span></div>
            <div className="table-container">
              <table>
                <thead><tr><th>#</th><th>Товар</th><th>Продано</th><th>Выручка</th></tr></thead>
                <tbody>
                  {d.top_products.map((p, i) => (
                    <tr key={i}><td>{i+1}</td><td style={{ fontWeight: 500 }}>{p.name}</td><td>{formatNumber(p.quantity)} шт.</td><td style={{ fontWeight: 600 }}>{formatCurrency(p.revenue)}</td></tr>
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
