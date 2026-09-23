'use client';
import { useState, useEffect } from 'react';
import { getProducts, getCategories } from '@/lib/api';
import { formatCurrency, formatNumber, trendBadge, riskColor, recTypeColor } from '@/lib/utils';
import Link from 'next/link';
import { Search, Filter, Package, ChevronLeft, ChevronRight } from 'lucide-react';

export default function ProductsPage() {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [search, setSearch] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [searchTimeout, setSearchTimeout] = useState(null);
  const pageSize = 30;

  const fetchProducts = async (p = page, s = search, c = categoryId) => {
    setLoading(true);
    try {
      const res = await getProducts({ page: p, page_size: pageSize, search: s || undefined, category_id: c || undefined });
      setProducts(res.items || []);
      setTotal(res.total || 0);
      setTotalPages(res.total_pages || 1);
    } catch {}
    setLoading(false);
  };

  useEffect(() => {
    getCategories().then(setCategories).catch(() => {});
  }, []);

  useEffect(() => { fetchProducts(); }, [page]);

  const handleSearch = (val) => {
    setSearch(val);
    if (searchTimeout) clearTimeout(searchTimeout);
    setSearchTimeout(setTimeout(() => {
      setPage(1);
      fetchProducts(1, val, categoryId);
    }, 400));
  };

  const handleCategoryChange = (val) => {
    setCategoryId(val);
    setPage(1);
    fetchProducts(1, search, val);
  };

  return (
    <>
      <div className="page-header">
        <div className="page-title-group">
          <h1 className="page-title">Товары</h1>
          <p className="page-subtitle">{formatNumber(total)} товаров в базе</p>
        </div>
      </div>

      <div className="page-content">
        {/* Filters */}
        <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
          <div style={{ position: 'relative', flex: 1, minWidth: 200 }}>
            <Search size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input
              className="input"
              placeholder="Поиск по названию, артикулу, штрихкоду..."
              value={search}
              onChange={(e) => handleSearch(e.target.value)}
              style={{ paddingLeft: 36 }}
            />
          </div>
          <select className="input" value={categoryId} onChange={(e) => handleCategoryChange(e.target.value)} style={{ width: 200 }}>
            <option value="">Все категории</option>
            {categories.map(c => (
              <option key={c.id} value={c.id}>{c.name} ({c.product_count})</option>
            ))}
          </select>
        </div>

        {/* Table */}
        {loading ? (
          <div className="loading-page"><div className="spinner" /></div>
        ) : products.length === 0 ? (
          <div className="empty-state">
            <Package size={48} />
            <p className="text-muted">Товары не найдены</p>
          </div>
        ) : (
          <>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Товар</th>
                    <th>Артикул</th>
                    <th>Категория</th>
                    <th>Цена</th>
                    <th>Остаток</th>
                    <th>Продажи 30д</th>
                    <th>Без продаж</th>
                    <th>Тренд</th>
                    <th>Риск</th>
                    <th>Рекомендация</th>
                  </tr>
                </thead>
                <tbody>
                  {products.map((p) => {
                    const tb = trendBadge(p.trend);
                    return (
                      <tr key={p.id}>
                        <td>
                          <Link href={`/dashboard/products/${p.id}`} style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                            {p.name}
                          </Link>
                        </td>
                        <td style={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>{p.sku}</td>
                        <td>{p.category_name || '—'}</td>
                        <td>{formatCurrency(p.sale_price)}</td>
                        <td>{formatNumber(p.total_quantity)} шт.</td>
                        <td>{p.sales_30d}</td>
                        <td>{p.days_without_sale} дн.</td>
                        <td><span className={`badge ${tb.cls}`}>{tb.label}</span></td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <div className="risk-bar">
                              <div className={`risk-bar-fill ${riskColor(p.risk_score)}`} style={{ width: `${p.risk_score}%` }} />
                            </div>
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{p.risk_score}</span>
                          </div>
                        </td>
                        <td><span className={`badge ${recTypeColor(p.recommendation)}`}>{p.recommendation || '—'}</span></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="pagination">
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}>
                <ChevronLeft size={14} />
              </button>
              {Array.from({ length: Math.min(7, totalPages) }, (_, i) => {
                let p;
                if (totalPages <= 7) p = i + 1;
                else if (page <= 4) p = i + 1;
                else if (page >= totalPages - 3) p = totalPages - 6 + i;
                else p = page - 3 + i;
                return (
                  <button key={p} className={page === p ? 'active' : ''} onClick={() => setPage(p)}>
                    {p}
                  </button>
                );
              })}
              <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}>
                <ChevronRight size={14} />
              </button>
            </div>
          </>
        )}
      </div>
    </>
  );
}
