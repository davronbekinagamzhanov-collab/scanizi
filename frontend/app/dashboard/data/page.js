'use client';

import { useState, useEffect } from 'react';
import { importFile, previewImport, getDataSources } from '@/lib/api';
import {
  Upload,
  FileSpreadsheet,
  CheckCircle,
  AlertTriangle,
} from 'lucide-react';

export default function DataPage() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [sources, setSources] = useState([]);

  const loadSources = async () => {
    try {
      const data = await getDataSources();
      setSources(data);
    } catch {
      setSources([]);
    }
  };

  useEffect(() => {
    loadSources();
  }, []);

  const handleFileSelect = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;

    setFile(f);
    setPreview(null);
    setResult(null);
    setError('');

    try {
      const pv = await previewImport(f);
      setPreview(pv);
    } catch (err) {
      setError(`?????? ?????????????: ${err.message}`);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setError('');
    setResult(null);

    try {
      const res = await importFile(file);

      if (!res.success) {
        setError(res.message || '?????? ?? ????????.');
        return;
      }

      setResult(res);
      setFile(null);
      setPreview(null);
      await loadSources();
    } catch (err) {
      setError(err.message || '?????? ???????.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <>
      <div className="page-header">
        <div className="page-title-group">
          <h1 className="page-title">??????????? ??????</h1>
          <p className="page-subtitle">
            ????????? ???????? ?????? ??????? ? ScanIZI ???????? ? ?????????????? ??.
          </p>
        </div>
      </div>

      <div className="page-content">
        <div className="card" style={{ maxWidth: 800, marginBottom: '1.5rem' }}>
          <div className="card-header">
            <span className="card-title">
              <FileSpreadsheet
                size={16}
                style={{ display: 'inline', marginRight: 6, verticalAlign: -3 }}
              />
              Excel / CSV
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div
              style={{
                border: '2px dashed var(--border-color)',
                borderRadius: 'var(--border-radius)',
                padding: '2.5rem',
                textAlign: 'center',
              }}
              onDragOver={(e) => e.preventDefault()}
              onDrop={async (e) => {
                e.preventDefault();

                const dropped = e.dataTransfer.files?.[0];
                if (!dropped) return;

                setFile(dropped);
                setPreview(null);
                setResult(null);
                setError('');

                try {
                  const pv = await previewImport(dropped);
                  setPreview(pv);
                } catch (err) {
                  setError(`?????? ?????????????: ${err.message}`);
                }
              }}
            >
              <Upload
                size={36}
                style={{ color: 'var(--text-muted)', marginBottom: 10 }}
              />

              <p
                className="text-muted"
                style={{ marginBottom: 10 }}
              >
                ?????????? ???????? ???? ??? ???????? ????
              </p>

              <label className="btn btn-primary btn-sm" style={{ cursor: 'pointer' }}>
                <input
                  type="file"
                  accept=".xlsx,.xls,.csv"
                  style={{ display: 'none' }}
                  onChange={handleFileSelect}
                />
                ??????? ????
              </label>

              {file && (
                <p
                  style={{
                    marginTop: 10,
                    fontSize: '0.875rem',
                    color: 'var(--accent-400)',
                  }}
                >
                  {file.name}
                </p>
              )}
            </div>

            {preview && (
              <div
                className="card"
                style={{
                  background: 'rgba(99,102,241,0.03)',
                  borderColor: 'var(--border-color)',
                }}
              >
                <div className="card-title" style={{ marginBottom: 8 }}>
                  ???????????? ?????
                </div>

                <p style={{ marginBottom: 4 }}>
                  <strong>?????:</strong>{' '}
                  {preview.total_rows ?? 0}
                </p>

                <p style={{ marginBottom: 4 }}>
                  <strong>?????????? ?????:</strong>{' '}
                  {preview.valid_rows ?? 0}
                </p>

                <p style={{ marginBottom: 8 }}>
                  <strong>??????:</strong>{' '}
                  {preview.error_rows ?? 0}
                </p>

                <p
                  className="text-muted"
                  style={{ fontSize: '0.75rem', lineHeight: 1.5 }}
                >
                  <strong>???????????? ???????:</strong>{' '}
                  {(preview.columns_detected || []).join(', ') || '?? ??????????'}
                </p>

                <button
                  className="btn btn-primary"
                  onClick={handleUpload}
                  disabled={uploading}
                  style={{ marginTop: 12 }}
                >
                  {uploading ? '??????...' : '????????????? ??????'}
                </button>
              </div>
            )}
          </div>
        </div>

        {result && (
          <div
            className="toast toast-success"
            style={{
              position: 'static',
              maxWidth: 800,
              marginBottom: '1rem',
            }}
          >
            <CheckCircle
              size={16}
              style={{ display: 'inline', verticalAlign: -3, marginRight: 6 }}
            />
            {result.message || '?????? ??????? ?????????????.'}
          </div>
        )}

        {error && (
          <div
            className="toast toast-error"
            style={{
              position: 'static',
              maxWidth: 800,
              marginBottom: '1rem',
            }}
          >
            <AlertTriangle
              size={16}
              style={{ display: 'inline', verticalAlign: -3, marginRight: 6 }}
            />
            {error}
          </div>
        )}

        <div className="card" style={{ maxWidth: 800 }}>
          <div className="card-header">
            <span className="card-title">????????? ??????</span>
          </div>

          {sources.length === 0 ? (
            <p className="text-muted">
              ????????? ??? ?? ??????????. ????????? ?????? Excel/CSV ????.
            </p>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>????????</th>
                    <th>???</th>
                    <th>??????</th>
                    <th>???????</th>
                    <th>????????? ?????????????</th>
                  </tr>
                </thead>
                <tbody>
                  {sources.map((s) => (
                    <tr key={s.id}>
                      <td>{s.name}</td>
                      <td>
                        <span className="badge badge-info">
                          {s.source_type}
                        </span>
                      </td>
                      <td>
                        <span className="badge badge-success">
                          ?????????
                        </span>
                      </td>
                      <td>{s.records_imported ?? 0}</td>
                      <td>{s.last_sync || '?'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
