/**
 * ScanIZI — API Client
 * All backend requests go through this module.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== 'undefined' &&
  window.location.hostname !== 'localhost' &&
  window.location.hostname !== '127.0.0.1'
    ? 'https://scanizi.onrender.com'
    : 'http://localhost:8000');

class ApiError extends Error {
  constructor(status, message, data) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

async function request(endpoint, options = {}) {
  const token = typeof window !== 'undefined' ? localStorage.getItem('scanizi_token') : null;

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Remove Content-Type for FormData
  if (options.body instanceof FormData) {
    delete headers['Content-Type'];
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('scanizi_token');
      localStorage.removeItem('scanizi_user');
      window.location.href = '/login';
    }
    throw new ApiError(401, 'Сессия истекла');
  }

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(response.status, data.detail || 'Ошибка сервера', data);
  }

  return response.json();
}

// ─── Auth ────────────────────────────────────────────
export async function login(username, password) {
  const data = await request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
  if (data.access_token) {
    localStorage.setItem('scanizi_token', data.access_token);
  }
  return data;
}

export async function getMe() {
  return request('/auth/me');
}

// ─── Dashboard ──────────────────────────────────────
export async function getDashboard() {
  return request('/dashboard');
}

// ─── Products ───────────────────────────────────────
export async function getProducts(params = {}) {
  const qs = new URLSearchParams();
  if (params.page) qs.set('page', params.page);
  if (params.page_size) qs.set('page_size', params.page_size);
  if (params.search) qs.set('search', params.search);
  if (params.category_id) qs.set('category_id', params.category_id);
  if (params.sort_by) qs.set('sort_by', params.sort_by);
  if (params.sort_order) qs.set('sort_order', params.sort_order);
  return request(`/products?${qs.toString()}`);
}

export async function getProduct(id) {
  return request(`/products/${id}`);
}

export async function getCategories() {
  return request('/products/categories');
}

// ─── Sales ──────────────────────────────────────────
export async function getSales(params = {}) {
  const qs = new URLSearchParams();
  if (params.days) qs.set('days', params.days);
  if (params.store_id) qs.set('store_id', params.store_id);
  if (params.page) qs.set('page', params.page);
  return request(`/sales?${qs.toString()}`);
}

export async function getSalesSummary(store_id) {
  const qs = store_id ? `?store_id=${store_id}` : '';
  return request(`/sales/summary${qs}`);
}

// ─── Capital ────────────────────────────────────────
export async function getCapital() {
  return request('/capital');
}

// ─── Stores ─────────────────────────────────────────
export async function getStores() {
  return request('/stores');
}

// ─── Warehouses ─────────────────────────────────────
export async function getWarehouses() {
  return request('/warehouses');
}

export async function getTransfers() {
  return request('/warehouses/transfers');
}

// ─── Employees ──────────────────────────────────────
export async function getEmployees() {
  return request('/employees');
}

export async function createEmployee(data) {
  return request('/employees', { method: 'POST', body: JSON.stringify(data) });
}

// ─── Scanner ────────────────────────────────────────
export async function scannerLookup(code) {
  return request(`/scanner/lookup?code=${encodeURIComponent(code)}`);
}

// ─── Data Sources ───────────────────────────────────
export async function getDataSources() {
  return request('/data/sources');
}

export async function importFile(file, warehouse_id = 1) {
  const formData = new FormData();
  formData.append('file', file);
  return request(`/data/import?warehouse_id=${warehouse_id}`, {
    method: 'POST',
    body: formData,
  });
}

export async function previewImport(file) {
  const formData = new FormData();
  formData.append('file', file);
  return request('/data/import/preview', {
    method: 'POST',
    body: formData,
  });
}

// ─── Recommendations ────────────────────────────────
export async function getRecommendations(limit = 20) {
  return request(`/recommendations?limit=${limit}`);
}

// ─── Demo ───────────────────────────────────────────
export async function loadDemoData() {
  return request('/demo/load', { method: 'POST' });
}

// ─── Health ─────────────────────────────────────────
export async function healthCheck() {
  return request('/health');
}

export { ApiError };
