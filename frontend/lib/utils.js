/**
 * ScanIZI — Utility helpers for formatting
 */

export function formatNumber(n, decimals = 0) {
  if (n == null || isNaN(n)) return '0';
  return new Intl.NumberFormat('ru-RU', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(n);
}

export function formatCurrency(n) {
  if (n == null || isNaN(n)) return '0 ₸';
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)} млн ₸`;
  if (n >= 1_000) return `${formatNumber(Math.round(n))} ₸`;
  return `${formatNumber(n, 2)} ₸`;
}

export function formatPercent(n) {
  if (n == null || isNaN(n)) return '0%';
  const sign = n > 0 ? '+' : '';
  return `${sign}${n.toFixed(1)}%`;
}

export function trendBadge(trend) {
  if (trend === 'growing') return { label: '↑ Рост', cls: 'badge-success' };
  if (trend === 'declining') return { label: '↓ Спад', cls: 'badge-danger' };
  return { label: '→ Стабильно', cls: 'badge-neutral' };
}

export function riskColor(score) {
  if (score >= 60) return 'risk-high';
  if (score >= 30) return 'risk-medium';
  return 'risk-low';
}

export function recTypeColor(type) {
  const map = {
    'RESTOCK': 'badge-info',
    'Пополнить': 'badge-info',
    'CONSIDER_DISCOUNT': 'badge-warning',
    'Рассмотреть скидку': 'badge-warning',
    'CONSIDER_RETURN': 'badge-danger',
    'Рассмотреть возврат': 'badge-danger',
    'CONSIDER_TRANSFER': 'badge-primary',
    'Рассмотреть перемещение': 'badge-primary',
    'DO_NOT_PURCHASE': 'badge-danger',
    'Не закупать пока': 'badge-danger',
    'OBSERVE': 'badge-neutral',
    'Наблюдать': 'badge-neutral',
    'NO_ACTION': 'badge-neutral',
    'Нет действий': 'badge-neutral',
  };
  return map[type] || 'badge-neutral';
}

export function pluralize(n, forms) {
  // Russian pluralization [1, 2-4, 5-20]
  const abs = Math.abs(n);
  const mod10 = abs % 10;
  const mod100 = abs % 100;
  if (mod10 === 1 && mod100 !== 11) return forms[0];
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return forms[1];
  return forms[2];
}
