'use client';
import { useState, useEffect, use } from 'react';
import { getProduct } from '@/lib/api';
import { formatCurrency, formatNumber, formatPercent, trendBadge, riskColor, recTypeColor } from '@/lib/utils';
import Link from 'next/link';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, BarChart, Bar } from 'recharts';
import { ArrowLeft, Package, TrendingUp, Warehouse, BrainCircuit, AlertTriangle, Info } from 'lucide-react';

export default function ProductDetailPage({ params }) {
  const { id } = use(params);
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getProduct(id).then(setProduct).catch(() => {}).finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="loading-page"><div className="spinner" /></div>;
  if (!product) return <div className="empty-state"><p>Товар не найден</p></div>;

  const p = product;
  const ai = p.ai_analysis || {};
  const tb = trendBadge(p.trend);

  return (
    <>
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Link href="/dashboard/products" className="btn btn-ghost"><ArrowLeft size={18} /></Link>
          <div className="page-title-group">
            <h1 className="page-title">{p.name}</h1>
            <p className="page-subtitle">{p.sku} · {p.category_name || 'Без категории'}</p>
          </div>
        </div>
        <span className={`badge ${recTypeColor(p.recommendation)}`}>{p.recommendation}</span>
      </div>

      <div className="page-content">
        {/* Metrics row */}
        <div className="grid-5" style={{ marginBottom: '1.5rem' }}>
          <div className="metric-card">
            <div className="metric-label">Остаток</div>
            <div className="metric-value">{formatNumber(p.total_quantity)} шт.</div>
            <div className="metric-sub">Запас на {p.days_of_stock > 9000 ? '∞' : `${Math.round(p.days_of_stock)} дней`}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Стоимость остатка</div>
            <div className="metric-value">{formatCurrency(p.total_inventory_value)}</div>
            <div className="metric-sub">Маржа: {formatPercent(p.margin_percent)}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Продажи 30д</div>
            <div className="metric-value">{formatNumber(p.sales_30d)} шт.</div>
            <div className="metric-sub">Скорость: {p.sales_velocity?.toFixed(1)} шт./день</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Динамика</div>
            <div className="metric-value" style={{ color: p.sales_change_percent > 0 ? 'var(--accent-400)' : p.sales_change_percent < -10 ? 'var(--danger-400)' : undefined }}>
              {formatPercent(p.sales_change_percent)}
            </div>
            <div className="metric-sub"><span className={`badge ${tb.cls}`}>{tb.label}</span></div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Риск</div>
            <div className="metric-value">{p.risk_score}/100</div>
            <div style={{ marginTop: 4 }}>
              <div className="risk-bar" style={{ width: '100%' }}>
                <div className={`risk-bar-fill ${riskColor(p.risk_score)}`} style={{ width: `${p.risk_score}%` }} />
              </div>
            </div>
          </div>
        </div>

        <div className="grid-2" style={{ marginBottom: '1.5rem' }}>
          {/* Sales chart */}
          <div className="card">
            <div className="card-header">
              <span className="card-title"><TrendingUp size={14} style={{ display: 'inline', marginRight: 6, verticalAlign: -2 }} />История продаж</span>
            </div>
            <div style={{ width: '100%', height: 220 }}>
              {p.sales_history?.length > 0 ? (
                <ResponsiveContainer>
                  <BarChart data={p.sales_history}>
                    <CartesianGrid stroke="rgba(99,102,241,0.06)" />
                    <XAxis dataKey="date" tick={{ fontSize: 9, fill: '#64748b' }} tickFormatter={v => v.slice(5)} interval="preserveStartEnd" />
                    <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
                    <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(99,102,241,0.2)', borderRadius: 8, fontSize: 12 }} />
                    <Bar dataKey="quantity" fill="#6366f1" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : <div className="empty-state"><p className="text-muted">Нет данных</p></div>}
            </div>
          </div>

          {/* AI Analysis */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">
                <BrainCircuit size={14} style={{ display: 'inline', marginRight: 6, verticalAlign: -2 }} />
                AI Анализ
                {ai.source === 'ai' && <span className="badge badge-primary" style={{ marginLeft: 8 }}>Gemini</span>}
                {ai.source === 'analytics' && <span className="badge badge-neutral" style={{ marginLeft: 8 }}>Аналитика</span>}
              </span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 4 }}>Рекомендация</div>
                <span className={`badge ${recTypeColor(ai.recommendation)}`} style={{ fontSize: '0.8125rem', padding: '0.375rem 0.875rem' }}>
                  {ai.recommendation}
                </span>
              </div>
              <div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 4 }}>Причина</div>
                <p style={{ fontSize: '0.875rem', lineHeight: 1.6, color: 'var(--text-secondary)' }}>{ai.reason}</p>
              </div>
              {ai.evidence && (
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 4 }}>Обоснование</div>
                  {ai.evidence.what_happened && <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: 4 }}>📊 {ai.evidence.what_happened}</p>}
                  {ai.evidence.why_important && <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: 4 }}>⚠️ {ai.evidence.why_important}</p>}
                  {ai.evidence.what_to_do && <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>💡 {ai.evidence.what_to_do}</p>}
                </div>
              )}
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <span className="badge badge-neutral">Уверенность: {ai.confidence}</span>
                {ai._fallback_notice && (
                  <span style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
                    <Info size={12} style={{ display: 'inline', verticalAlign: -2, marginRight: 4 }} />
                    {ai._fallback_notice}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Inventory by warehouse */}
        {p.inventory_by_warehouse?.length > 0 && (
          <div className="card">
            <div className="card-header">
              <span className="card-title"><Warehouse size={14} style={{ display: 'inline', marginRight: 6, verticalAlign: -2 }} />Остатки по складам</span>
            </div>
            <div className="table-container">
              <table>
                <thead>
                  <tr><th>Магазин</th><th>Склад</th><th>Количество</th><th>Стоимость</th></tr>
                </thead>
                <tbody>
                  {p.inventory_by_warehouse.map((w, i) => (
                    <tr key={i}>
                      <td>{w.store_name}</td>
                      <td>{w.warehouse_name}</td>
                      <td style={{ fontWeight: 600 }}>{formatNumber(w.quantity)} шт.</td>
                      <td>{formatCurrency(w.value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Price info */}
        <div className="grid-3" style={{ marginTop: '1rem' }}>
          <div className="card">
            <div className="card-title" style={{ marginBottom: '0.5rem' }}>Цены</div>
            <div style={{ display: 'grid', gap: '0.375rem', fontSize: '0.875rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span className="text-muted">Закупочная</span><span>{formatCurrency(p.purchase_price)}</span></div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span className="text-muted">Продажная</span><span>{formatCurrency(p.sale_price)}</span></div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span className="text-muted">Маржа</span><span style={{ color: 'var(--accent-400)' }}>{formatCurrency(p.margin)} ({formatPercent(p.margin_percent)})</span></div>
            </div>
          </div>
          <div className="card">
            <div className="card-title" style={{ marginBottom: '0.5rem' }}>Продажи</div>
            <div style={{ display: 'grid', gap: '0.375rem', fontSize: '0.875rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span className="text-muted">7 дней</span><span>{p.sales_7d} шт.</span></div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span className="text-muted">30 дней</span><span>{p.sales_30d} шт.</span></div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span className="text-muted">90 дней</span><span>{p.sales_90d} шт.</span></div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span className="text-muted">Посл. продажа</span><span>{p.last_sale_date || '—'}</span></div>
            </div>
          </div>
          <div className="card">
            <div className="card-title" style={{ marginBottom: '0.5rem' }}>Складские метрики</div>
            <div style={{ display: 'grid', gap: '0.375rem', fontSize: '0.875rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span className="text-muted">Оборачиваемость</span><span>{p.turnover_days > 9000 ? '∞' : `${Math.round(p.turnover_days)} дн.`}</span></div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span className="text-muted">Без продаж</span><span>{p.days_without_sale} дн.</span></div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span className="text-muted">Дефицит</span><span>{p.deficit_risk ? '⚠️ Да' : '✅ Нет'}</span></div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span className="text-muted">Сезонный</span><span>{p.is_seasonal ? 'Да' : 'Нет'}</span></div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
