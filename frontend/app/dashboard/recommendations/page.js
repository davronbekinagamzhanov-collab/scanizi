'use client';
import { useState, useEffect } from 'react';
import { getRecommendations } from '@/lib/api';
import { formatCurrency, formatPercent, trendBadge, recTypeColor } from '@/lib/utils';
import Link from 'next/link';
import { BrainCircuit } from 'lucide-react';

export default function RecommendationsPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getRecommendations(50).then(setData).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading-page"><div className="spinner" /></div>;

  const items = data?.items || [];

  return (
    <>
      <div className="page-header">
        <div className="page-title-group">
          <h1 className="page-title">AI Рекомендации</h1>
          <p className="page-subtitle">{items.length} товаров требуют внимания {data?.ai_available ? <span className="badge badge-primary" style={{ marginLeft: 6 }}>Gemini активен</span> : <span className="badge badge-neutral" style={{ marginLeft: 6 }}>Аналитика</span>}</p>
        </div>
      </div>
      <div className="page-content">
        {items.length === 0 ? (
          <div className="empty-state"><BrainCircuit size={48} /><h3>Нет активных рекомендаций</h3><p className="text-muted">Все товары в норме</p></div>
        ) : (
          <div className="table-container">
            <table>
              <thead><tr><th>Приоритет</th><th>Товар</th><th>Категория</th><th>Рекомендация</th><th>Риск</th><th>Стоимость остатка</th><th>Продажи 30д</th><th>Тренд</th><th>Уверенность</th></tr></thead>
              <tbody>
                {items.map((item, i) => {
                  const tb = trendBadge(item.trend);
                  return (
                    <tr key={i}>
                      <td><span className={`badge ${item.priority >= 50 ? 'badge-danger' : item.priority >= 25 ? 'badge-warning' : 'badge-neutral'}`}>{item.priority}</span></td>
                      <td><Link href={`/dashboard/products/${item.product_id}`} style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{item.product_name}</Link></td>
                      <td>{item.category || '—'}</td>
                      <td><span className={`badge ${recTypeColor(item.rec_type_label)}`}>{item.rec_type_label}</span></td>
                      <td>{item.risk_score}</td>
                      <td>{formatCurrency(item.inventory_value)}</td>
                      <td>{item.sales_30d}</td>
                      <td><span className={`badge ${tb.cls}`}>{tb.label}</span></td>
                      <td><span className="badge badge-neutral">{item.confidence}</span></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
