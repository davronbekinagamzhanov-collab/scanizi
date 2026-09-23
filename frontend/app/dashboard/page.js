'use client';
/**
 * ScanIZI — Main Dashboard page
 * Real data from backend API, not hardcoded.
 */
import { useState, useEffect } from 'react';
import { getDashboard } from '@/lib/api';
import { formatCurrency, formatNumber, formatPercent, trendBadge, riskColor, recTypeColor } from '@/lib/utils';
import { useAuth } from '@/lib/auth';
import Link from 'next/link';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid
} from 'recharts';
import {
  AlertTriangle, TrendingDown, TrendingUp, Package, DollarSign,
  Activity, ShoppingCart, Warehouse, BrainCircuit
} from 'lucide-react';

export default function DashboardPage() {
  const { isOwner } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getDashboard();
      setData(res);
    } catch (err) {
      setError(err.message || 'Ошибка загрузки данных');
    }
    setLoading(false);
  };

  useEffect(() => { fetchData(); }, []);



  if (loading) {
    return (
      <div className="loading-page">
        <div className="spinner" />
        <p className="text-muted">Загрузка аналитики...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-content">
        <div className="empty-state">
          <AlertTriangle size={48} />
          <h3>Ошибка загрузки</h3>
          <p className="text-muted">{error}</p>
          <button className="btn btn-primary" onClick={fetchData}>Повторить</button>
        </div>
      </div>
    );
  }

  const m = data?.metrics || {};
  const attention = data?.attention_items || [];
  const frozen = data?.frozen_capital_items || [];
  const chart = data?.sales_chart || [];

  // Empty installation: show onboarding prompt.
  if (m.total_products === 0) {
    return (
      <div className="page-content">
        <div className="empty-state">
          <Package size={64} />
          <h2>ScanIZI готов к работе</h2>
          <p className="text-muted" style={{ maxWidth: 440 }}>
            В базе пока нет товаров. Загрузите прайс-лист в формате
            Excel или CSV, чтобы система начала анализировать
            остатки и строить аналитику.
          </p>
          {isOwner && (
            <Link href="/dashboard/data" className="btn btn-primary">
              Загрузить Excel / CSV
            </Link>
          )}
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="page-header">
        <div className="page-title-group">
          <h1 className="page-title">Обзор</h1>
          <p className="page-subtitle">Ключевые метрики вашего бизнеса</p>
        </div>
      </div>

      <div className="page-content">
        {/* ─── Metric Cards ─────────────────────────────── */}
        <div className="grid-5" style={{ marginBottom: '1.5rem' }}>
          <div className="metric-card">
            <div className="metric-label">Стоимость остатков</div>
            <div className="metric-value">{formatCurrency(m.total_inventory_value)}</div>
            <div className="metric-sub">{formatNumber(m.total_products)} товаров</div>
          </div>
          <div className="metric-card" style={{ borderColor: m.frozen_capital_percent > 20 ? 'rgba(244,63,94,0.3)' : undefined }}>
            <div className="metric-label">Замороженный капитал</div>
            <div className="metric-value" style={{ color: m.frozen_capital_percent > 20 ? 'var(--danger-400)' : undefined }}>
              {formatCurrency(m.frozen_capital)}
            </div>
            <div className="metric-sub">{formatPercent(m.frozen_capital_percent)} от остатков</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Продажи 30 дней</div>
            <div className="metric-value">{formatCurrency(m.sales_30d)}</div>
            <div className="metric-sub">Средний оборот: {formatNumber(m.turnover_days)} дней</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">⚠ Товары в зоне риска</div>
            <div className="metric-value" style={{ color: m.products_at_risk > 0 ? 'var(--warning-400)' : undefined }}>
              {formatNumber(m.products_at_risk)}
            </div>
            <div className="metric-sub">Высокий оборот / большие остатки</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Риск дефицита</div>
            <div className="metric-value" style={{ color: m.potential_deficit > 0 ? 'var(--danger-400)' : undefined }}>
              {formatNumber(m.potential_deficit)}
            </div>
            <div className="metric-sub">Запас &lt; 14 дней</div>
          </div>
        </div>

        {/* ─── Sales Chart + Attention ─────────────────── */}
        <div className="grid-2" style={{ marginBottom: '1.5rem' }}>
          {/* Sales Chart */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">
                <ShoppingCart size={14} style={{ display: 'inline', marginRight: 6, verticalAlign: -2 }} />
                Продажи за 30 дней
              </span>
            </div>
            <div style={{ width: '100%', height: 220 }}>
              {chart.length > 0 ? (
                <ResponsiveContainer>
                  <AreaChart data={chart}>
                    <defs>
                      <linearGradient id="salesGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#6366f1" stopOpacity={0.3} />
                        <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="rgba(99,102,241,0.06)" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 10, fill: '#64748b' }}
                      tickFormatter={(v) => v.slice(5)}
                      interval="preserveStartEnd"
                    />
                    <YAxis tick={{ fontSize: 10, fill: '#64748b' }} tickFormatter={(v) => v >= 1000 ? `${(v/1000).toFixed(0)}k` : v} />
                    <Tooltip
                      contentStyle={{ background: '#1e293b', border: '1px solid rgba(99,102,241,0.2)', borderRadius: 8, fontSize: 12 }}
                      labelStyle={{ color: '#94a3b8' }}
                      formatter={(v) => [formatCurrency(v), 'Выручка']}
                    />
                    <Area type="monotone" dataKey="total" stroke="#6366f1" fill="url(#salesGradient)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="empty-state" style={{ padding: '2rem' }}>
                  <p className="text-muted">Нет данных о продажах</p>
                </div>
              )}
            </div>
          </div>

          {/* Attention Items */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">
                <BrainCircuit size={14} style={{ display: 'inline', marginRight: 6, verticalAlign: -2 }} />
                Требуют внимания
              </span>
              <Link href="/dashboard/recommendations" className="btn btn-sm btn-secondary">
                Все
              </Link>
            </div>
            {attention.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {attention.map((item, i) => {
                  const tb = trendBadge(item.trend);
                  return (
                    <Link
                      href={`/dashboard/products/${item.product_id}`}
                      key={i}
                      style={{
                        display: 'flex', alignItems: 'center', gap: '0.75rem',
                        padding: '0.625rem 0.5rem', borderRadius: 8,
                        background: 'rgba(99,102,241,0.03)', textDecoration: 'none',
                        transition: 'background 0.15s',
                      }}
                      onMouseOver={(e) => e.currentTarget.style.background = 'rgba(99,102,241,0.08)'}
                      onMouseOut={(e) => e.currentTarget.style.background = 'rgba(99,102,241,0.03)'}
                    >
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {item.product_name}
                        </div>
                        <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', marginTop: 2 }}>
                          {formatCurrency(item.inventory_value)} · {item.sales_30d} продаж/30д
                        </div>
                      </div>
                      <span className={`badge ${recTypeColor(item.rec_type_label)}`}>
                        {item.rec_type_label}
                      </span>
                    </Link>
                  );
                })}
              </div>
            ) : (
              <div className="empty-state" style={{ padding: '2rem' }}>
                <p className="text-muted">Нет критических проблем</p>
              </div>
            )}
          </div>
        </div>

        {/* ─── Frozen Capital Table ─────────────────────── */}
        {frozen.length > 0 && (
          <div className="card">
            <div className="card-header">
              <span className="card-title">
                <DollarSign size={14} style={{ display: 'inline', marginRight: 6, verticalAlign: -2 }} />
                Замороженный капитал — ТОП товары
              </span>
              {isOwner && (
                <Link href="/dashboard/capital" className="btn btn-sm btn-secondary">Подробнее</Link>
              )}
            </div>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Товар</th>
                    <th>Стоимость остатка</th>
                    <th>Продажи 30д</th>
                    <th>Без продаж</th>
                    <th>Оборот</th>
                    <th>Тренд</th>
                  </tr>
                </thead>
                <tbody>
                  {frozen.slice(0, 8).map((item, i) => {
                    const tb = trendBadge(item.trend);
                    return (
                      <tr key={i}>
                        <td>
                          <Link href={`/dashboard/products/${item.product_id}`} style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                            {item.product_name}
                          </Link>
                        </td>
                        <td style={{ fontWeight: 600 }}>{formatCurrency(item.inventory_value)}</td>
                        <td>{item.sales_30d} шт.</td>
                        <td>{item.days_without_sale} дн.</td>
                        <td>{item.turnover_days > 9000 ? '∞' : `${Math.round(item.turnover_days)} дн.`}</td>
                        <td><span className={`badge ${tb.cls}`}>{tb.label}</span></td>
                      </tr>
                    );
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
