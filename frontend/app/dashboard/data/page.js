'use client';
import { useState } from 'react';
import { importFile, previewImport, loadDemoData, getDataSources } from '@/lib/api';
import { Database, Upload, FileSpreadsheet, CheckCircle, AlertTriangle, Loader2 } from 'lucide-react';
import { useEffect } from 'react';

export default function DataPage() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loadingDemo, setLoadingDemo] = useState(false);
  const [sources, setSources] = useState([]);

  useEffect(() => {
    getDataSources().then(setSources).catch(() => {});
  }, []);

  const handleFileSelect = async (e) => {
    const f = e.target.files[0];
    if (!f) return;
    setFile(f);
    setResult(null);
    setError('');
    try {
      const pv = await previewImport(f);
      setPreview(pv);
    } catch (err) {
      setError(`Ошибка предпросмотра: ${err.message}`);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    try {
      const res = await importFile(file);
      setResult(res);
      setFile(null);
      setPreview(null);
    } catch (err) {
      setError(err.message);
    }
    setUploading(false);
  };

  const handleLoadDemo = async () => {
    setLoadingDemo(true);
    try {
      const res = await loadDemoData();
      setResult(res);
    } catch (err) {
      setError(err.message);
    }
    setLoadingDemo(false);
  };

  return (
    <>
      <div className="page-header">
        <div className="page-title-group">
          <h1 className="page-title">Данные</h1>
          <p className="page-subtitle">Импорт товаров и управление источниками</p>
        </div>
      </div>
      <div className="page-content">
        <div className="grid-2" style={{ marginBottom: '1.5rem' }}>
          {/* File Import */}
          <div className="card">
            <div className="card-header"><span className="card-title"><FileSpreadsheet size={14} style={{ display: 'inline', marginRight: 6, verticalAlign: -2 }} />Импорт Excel/CSV</span></div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ border: '2px dashed var(--border-color)', borderRadius: 'var(--border-radius)', padding: '2rem', textAlign: 'center', cursor: 'pointer', transition: 'border-color 0.2s' }} onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) { setFile(f); } }}>
                <Upload size={32} style={{ color: 'var(--text-muted)', marginBottom: 8 }} />
                <p className="text-muted" style={{ marginBottom: 8 }}>Перетащите файл сюда или</p>
                <label className="btn btn-secondary btn-sm" style={{ cursor: 'pointer' }}>
                  <input type="file" accept=".xlsx,.xls,.csv" style={{ display: 'none' }} onChange={handleFileSelect} />
                  Выберите файл
                </label>
                {file && <p style={{ marginTop: 8, fontSize: '0.875rem', color: 'var(--accent-400)' }}>{file.name}</p>}
              </div>

              {preview && (
                <div style={{ fontSize: '0.875rem' }}>
                  <p><strong>Найдено:</strong> {preview.rows_found} строк, {preview.columns?.length} столбцов</p>
                  <p className="text-muted" style={{ fontSize: '0.75rem' }}>Столбцы: {preview.columns?.join(', ')}</p>
                  <button className="btn btn-primary" onClick={handleUpload} disabled={uploading} style={{ marginTop: 8 }}>
                    {uploading ? 'Импорт...' : 'Импортировать'}
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Demo data */}
          <div className="card">
            <div className="card-header"><span className="card-title"><Database size={14} style={{ display: 'inline', marginRight: 6, verticalAlign: -2 }} />Демо-данные</span></div>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '1rem', lineHeight: 1.6 }}>
              Генерирует ~2000 товаров, 2 магазина, 3 склада и 12 месяцев истории продаж с реалистичными паттернами (A-F сценарии).
            </p>
            <button className="btn btn-primary" onClick={handleLoadDemo} disabled={loadingDemo}>
              <Database size={16} />
              {loadingDemo ? 'Генерация...' : 'Загрузить демо-данные'}
            </button>
          </div>
        </div>

        {/* Result message */}
        {result && (
          <div className={`toast ${result.error ? 'toast-error' : 'toast-success'}`} style={{ position: 'static', maxWidth: '100%', marginBottom: '1rem' }}>
            <CheckCircle size={16} style={{ display: 'inline', verticalAlign: -3, marginRight: 6 }} />
            {result.message || `Импорт завершён. ${result.products_imported || 0} товаров.`}
          </div>
        )}

        {error && (
          <div className="toast toast-error" style={{ position: 'static', maxWidth: '100%', marginBottom: '1rem' }}>
            <AlertTriangle size={16} style={{ display: 'inline', verticalAlign: -3, marginRight: 6 }} />
            {error}
          </div>
        )}

        {/* Data Sources */}
        {sources.length > 0 && (
          <div className="card">
            <div className="card-header"><span className="card-title">Подключённые источники</span></div>
            <div className="table-container">
              <table>
                <thead><tr><th>Тип</th><th>Название</th><th>Статус</th><th>Последний импорт</th></tr></thead>
                <tbody>
                  {sources.map((s, i) => (
                    <tr key={i}>
                      <td><span className="badge badge-info">{s.source_type}</span></td>
                      <td>{s.name}</td>
                      <td><span className={`badge ${s.status === 'active' ? 'badge-success' : 'badge-neutral'}`}>{s.status === 'active' ? 'Активен' : s.status}</span></td>
                      <td>{s.last_sync || '—'}</td>
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
