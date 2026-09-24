/**
 * ScanIZI — API Client
 * Hardened: timeouts, error normalization, auth handling, no infinite loading.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const DEFAULT_TIMEOUT_MS = 10000;   // 10s — normal requests
const AI_TIMEOUT_MS = 20000;        // 20s — AI analysis
const UPLOAD_TIMEOUT_MS = 60000;    // 60s — file uploads

class ApiError extends Error {
  constructor(status, message, data) {
    super(message);
    this.status = status;
    this.data = data;
    this.name = 'ApiError';
  }
}

function normalizeError(err) {
  if (err.name === 'AbortError') {
    return new ApiError(408, 'Превышено время ожидания. Проверьте соединение.', {});
  }
  if (err instanceof ApiError) return err;
  if (typeof navigator !== 'undefined' && !navigator.onLine) {
    return new ApiError(0, 'Нет интернет-соединения.', {});
  }
  return new ApiError(0, err.message || 'Сетевая ошибка', {});
}

async function request(endpoint, options = {}, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const token = typeof window !== 'undefined' ? localStorage.getItem('scanizi_token') : null;

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Remove Content-Type for FormData — browser sets it with boundary
  if (options.body instanceof FormData) {
    delete headers['Content-Type'];
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
      signal: controller.signal,
    });

    clearTimeout(timer);

    if (response.status === 401) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('scanizi_token');
        localStorage.removeItem('scanizi_user');
        window.location.href = '/login';
      }
      throw new ApiError(401, 'Сессия истекла. Войдите снова.');
    }

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new ApiError(
        response.status,
        data.detail || `Ошибка сервера (${response.status})`,
        data
      );
    }

    return response.json();
  } catch (err) {
    clearTimeout(timer);
    if (err instanceof ApiError) throw err;
    throw normalizeError(err);
  }
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

// ─── AI Insights (separate, non-blocking) ───────────
export async function getAiInsights() {
  return request('/ai/insights', {}, AI_TIMEOUT_MS);
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

/**
 * Record a sale transaction (ACID: updates inventory automatically).
 * @param {object} data - { product_id, store_id, warehouse_id, quantity, unit_price }
 */
export async function recordSale(data) {
  return request('/sales', {
    method: 'POST',
    body: JSON.stringify(data),
  });
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

export async function deleteDataSource(id) {
  return request(`/data/sources/${id}`, { method: 'DELETE' });
}

/**
 * Step 1: AI analyzes file structure — returns column mapping + summary.
 * Does NOT import anything. Timeout: 20s.
 * @param {File} file
 */
export async function analyzeExcelWithAI(file) {
  const formData = new FormData();
  formData.append('file', file);
  return request('/data/ai-analyze', {
    method: 'POST',
    body: formData,
  }, AI_TIMEOUT_MS);
}

/**
 * Step 2: Import file into PostgreSQL with optional AI column mapping.
 * Snapshot mode: quantity in Excel = actual quantity (replaces DB value).
 * @param {File} file
 * @param {number|null} warehouse_id
 * @param {object|null} columnMapping - AI-suggested column mapping
 */
export async function importFile(file, warehouse_id = null, columnMapping = null) {
  const formData = new FormData();
  formData.append('file', file);
  if (columnMapping) {
    formData.append('column_mapping', JSON.stringify(columnMapping));
  }
  const qs = warehouse_id ? `?warehouse_id=${warehouse_id}` : '';
  return request(`/data/import${qs}`, {
    method: 'POST',
    body: formData,
  }, UPLOAD_TIMEOUT_MS);
}

export async function previewImport(file) {
  const formData = new FormData();
  formData.append('file', file);
  return request('/data/import/preview', {
    method: 'POST',
    body: formData,
  }, UPLOAD_TIMEOUT_MS);
}

// ─── Recommendations ────────────────────────────────
export async function getRecommendations(limit = 20) {
  return request(`/recommendations?limit=${limit}`);
}

// ─── Health ─────────────────────────────────────────
export async function healthCheck() {
  return request('/health', {}, 5000);
}

export { ApiError };
