'use client';
/**
 * ScanIZI — Scanner Page
 * Camera barcode scanning via BarcodeDetector API (Chrome/Edge) with graceful fallback to manual input.
 * No external library needed for camera path. Falls back to text input if BarcodeDetector unavailable.
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { scannerLookup } from '@/lib/api';
import { formatCurrency, formatNumber } from '@/lib/utils';
import { ScanBarcode, Search, Package, Camera, CameraOff, X, AlertCircle } from 'lucide-react';
import Link from 'next/link';

/* ─── Camera Scanner component ──────────────────────────────────────────── */
import { Html5Qrcode } from 'html5-qrcode';

function CameraScanner({ onDetect, onClose }) {
  const [status, setStatus] = useState('starting'); // starting | scanning | error
  const [errorMsg, setErrorMsg] = useState('');
  const scannerRef = useRef(null);

  useEffect(() => {
    let mounted = true;
    const scannerId = "reader";

    const startCamera = async () => {
      try {
        const html5QrCode = new Html5Qrcode(scannerId);
        scannerRef.current = html5QrCode;
        
        await html5QrCode.start(
          { facingMode: "environment" },
          {
            fps: 10,
            qrbox: { width: 250, height: 150 },
            formatsToSupport: [0, 1, 3, 4, 8, 11] // CODE_128, CODE_39, EAN_13, EAN_8, QR_CODE, DATA_MATRIX
          },
          (decodedText, decodedResult) => {
            if (mounted) {
              onDetect(decodedText);
              html5QrCode.stop().catch(console.error);
            }
          },
          (errorMessage) => {
            // parse errors are normal (frame didn't contain code)
          }
        );
        if (mounted) setStatus('scanning');
      } catch (err) {
        if (!mounted) return;
        setStatus('error');
        if (err?.name === 'NotAllowedError' || err?.message?.includes('Permission')) {
          setErrorMsg('Доступ к камере запрещён. Разрешите доступ в настройках браузера.');
        } else {
          setErrorMsg(`Ошибка камеры: ${err?.message || 'Неизвестная ошибка'}`);
        }
      }
    };

    startCamera();

    return () => {
      mounted = false;
      if (scannerRef.current && scannerRef.current.isScanning) {
        scannerRef.current.stop().catch(console.error);
      }
    };
  }, [onDetect]);

  return (
    <div style={{
      position: 'relative', borderRadius: 'var(--border-radius-lg)',
      overflow: 'hidden', background: '#000',
      maxWidth: 480, width: '100%', margin: '0 auto'
    }}>
      <button
        onClick={onClose}
        style={{
          position: 'absolute', top: 10, right: 10, zIndex: 10,
          background: 'rgba(0,0,0,0.6)', border: 'none', borderRadius: '50%',
          width: 36, height: 36, display: 'flex', alignItems: 'center',
          justifyContent: 'center', cursor: 'pointer', color: 'white',
        }}
        aria-label="Закрыть камеру"
      >
        <X size={18} />
      </button>

      <div id="reader" style={{ width: '100%', minHeight: 300, background: '#000' }}></div>

      {status === 'starting' && (
        <div style={{
          position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', gap: '0.75rem', color: 'white',
          background: '#000'
        }}>
          <div className="spinner" />
          <span style={{ fontSize: '0.875rem', color: 'rgba(255,255,255,0.7)' }}>Запуск камеры...</span>
        </div>
      )}

      {status === 'error' && (
        <div style={{
          position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', gap: '0.75rem',
          color: 'var(--danger-400)', padding: '1.5rem', textAlign: 'center',
          background: '#000'
        }}>
          <AlertCircle size={36} />
          <span style={{ fontSize: '0.875rem', lineHeight: 1.5 }}>{errorMsg}</span>
        </div>
      )}
    </div>
  );
}

/* ─── Main Scanner Page ──────────────────────────────────────────────────── */
export default function ScannerPage() {
  const [code, setCode] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [cameraMode, setCameraMode] = useState(false);
  const [cameraSupported, setCameraSupported] = useState(false);
  const inputRef = useRef(null);

  // Detect camera support on mount
  useEffect(() => {
    const hasMedia = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    setCameraSupported(hasMedia);
  }, []);

  const doLookup = useCallback(async (barcode) => {
    const trimmed = barcode.trim();
    if (!trimmed) return;
    setCode(trimmed);
    setLoading(true);
    setSearched(true);
    setCameraMode(false);
    try {
      const res = await scannerLookup(trimmed);
      setResult(res);
    } catch (err) {
      setResult({ found: false, message: err.message || 'Ошибка поиска' });
    }
    setLoading(false);
    // Focus back to input for quick re-scan
    setTimeout(() => inputRef.current?.focus(), 100);
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    doLookup(code);
  };

  const handleCameraDetect = (detectedCode) => {
    setCameraMode(false);
    doLookup(detectedCode);
  };

  const handleReset = () => {
    setCode('');
    setResult(null);
    setSearched(false);
    inputRef.current?.focus();
  };

  return (
    <>
      <div className="page-header">
        <div className="page-title-group">
          <h1 className="page-title">Сканер</h1>
          <p className="page-subtitle">Поиск товара по штрихкоду или артикулу</p>
        </div>
      </div>

      <div className="page-content">
        {/* ─── Search bar ─────────────────── */}
        <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.25rem', maxWidth: 540 }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <ScanBarcode
              size={18}
              style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' }}
              aria-hidden="true"
            />
            <input
              ref={inputRef}
              className="input"
              placeholder="Штрихкод или артикул..."
              value={code}
              onChange={e => setCode(e.target.value)}
              style={{ paddingLeft: 40 }}
              autoFocus
              autoComplete="off"
              aria-label="Штрихкод или артикул товара"
            />
          </div>
          <button type="submit" className="btn btn-primary" disabled={loading || !code.trim()}>
            <Search size={16} aria-hidden="true" />
            Найти
          </button>
          {cameraSupported && (
            <button
              type="button"
              className={`btn ${cameraMode ? 'btn-danger' : 'btn-secondary'}`}
              onClick={() => setCameraMode(!cameraMode)}
              title={cameraMode ? 'Закрыть камеру' : 'Сканировать камерой'}
              aria-label={cameraMode ? 'Закрыть камеру' : 'Открыть камеру для сканирования'}
            >
              {cameraMode ? <CameraOff size={18} aria-hidden="true" /> : <Camera size={18} aria-hidden="true" />}
            </button>
          )}
        </form>

        {/* ─── Camera scanner ────────────── */}
        {cameraMode && (
          <div style={{ marginBottom: '1.5rem' }}>
            <CameraScanner
              onDetect={handleCameraDetect}
              onClose={() => setCameraMode(false)}
            />
          </div>
        )}

        {/* ─── Loading ───────────────────── */}
        {loading && (
          <div className="loading-page" style={{ minHeight: '30vh' }}>
            <div className="spinner" />
          </div>
        )}

        {/* ─── Result ────────────────────── */}
        {searched && !loading && result && (
          result.found ? (
            <div className="card" style={{ maxWidth: 600 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                <h3 style={{ color: 'var(--text-primary)' }}>{result.product.name}</h3>
                <button
                  className="btn btn-sm btn-secondary"
                  onClick={handleReset}
                  aria-label="Очистить результат"
                >
                  <X size={14} />
                </button>
              </div>

              <div style={{ display: 'grid', gap: '0.375rem', fontSize: '0.875rem', marginBottom: '1rem' }}>
                {[
                  ['Артикул', <span style={{ fontFamily: 'monospace' }}>{result.product.sku}</span>],
                  ['Штрихкод', <span style={{ fontFamily: 'monospace' }}>{result.product.barcode || '—'}</span>],
                  ['Категория', result.product.category || '—'],
                  ['Ед. измерения', result.product.unit || '—'],
                  ['Цена закупки', formatCurrency(result.product.purchase_price)],
                  ['Цена продажи', <span style={{ fontWeight: 600 }}>{formatCurrency(result.product.sale_price)}</span>],
                  ['Общий остаток', <span style={{ fontWeight: 700, color: 'var(--accent-400)' }}>{formatNumber(result.total_quantity)} шт.</span>],
                ].map(([label, value]) => (
                  <div key={label} style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem' }}>
                    <span className="text-muted">{label}</span>
                    <span>{value}</span>
                  </div>
                ))}
              </div>

              {result.inventory.length > 0 && (
                <>
                  <div className="card-title" style={{ marginBottom: '0.5rem' }}>Остатки по складам</div>
                  <div className="table-container">
                    <table>
                      <thead>
                        <tr>
                          <th>Магазин</th>
                          <th>Склад</th>
                          <th>Количество</th>
                        </tr>
                      </thead>
                      <tbody>
                        {result.inventory.map((inv, i) => (
                          <tr key={i}>
                            <td>{inv.store}</td>
                            <td>{inv.warehouse}</td>
                            <td style={{ fontWeight: 600, color: inv.quantity === 0 ? 'var(--danger-400)' : 'var(--accent-400)' }}>
                              {formatNumber(inv.quantity)} шт.
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              )}

              <div style={{ marginTop: '1rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border-color)', display: 'flex', gap: '8px' }}>
                <Link href={`/dashboard/products/${result.product.id}`} className="btn btn-sm btn-secondary">
                  Карточка товара →
                </Link>
                <Link href={`/dashboard/sales?code=${result.product.sku}&mode=sale`} className="btn btn-sm btn-primary">
                  Продать
                </Link>
                <Link href={`/dashboard/sales?code=${result.product.sku}&mode=purchase`} className="btn btn-sm btn-success">
                  Приход
                </Link>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <Package size={48} />
              <h3>Товар не найден</h3>
              <p className="text-muted">{result.message}</p>
              <button className="btn btn-secondary" onClick={handleReset}>Новый поиск</button>
            </div>
          )
        )}

        {/* ─── Hint (only when idle) ─────── */}
        {!searched && !cameraMode && (
          <div className="card" style={{ maxWidth: 480, borderStyle: 'dashed' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
              <p style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Как пользоваться сканером</p>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <ScanBarcode size={16} style={{ flexShrink: 0, color: 'var(--primary-400)', marginTop: 2 }} />
                <span>Введите штрихкод или артикул в поле поиска</span>
              </div>
              {cameraSupported && (
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <Camera size={16} style={{ flexShrink: 0, color: 'var(--primary-400)', marginTop: 2 }} />
                  <span>Или нажмите кнопку камеры для авто-сканирования</span>
                </div>
              )}
              {!cameraSupported && (
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <AlertCircle size={16} style={{ flexShrink: 0, color: 'var(--text-muted)', marginTop: 2 }} />
                  <span className="text-muted">Для работы авто-сканирования разрешите доступ к камере или используйте HTTPS</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </>
  );
}
