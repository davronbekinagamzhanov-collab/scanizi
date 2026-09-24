'use client';

import { useState, useEffect, useRef } from 'react';
import {
  analyzeExcelWithAI,
  importFile,
  getDataSources,
  deleteDataSource,
} from '@/lib/api';

// ─── Field label map ─────────────────────────────────────────────────────────
const FIELD_LABELS = {
  name: 'Название',
  sku: 'Артикул',
  barcode: 'Штрихкод',
  sale_price: 'Цена продажи',
  purchase_price: 'Закупочная цена',
  quantity: 'Остаток',
  category: 'Категория',
  unit: 'Единица',
};

const QUALITY_LABELS = {
  good: { label: 'Хорошее', color: '#22c55e' },
  ok: { label: 'Нормальное', color: '#f59e0b' },
  poor: { label: 'Плохое', color: '#ef4444' },
};

export default function DataPage() {
  const [file, setFile] = useState(null);
  const [step, setStep] = useState('idle'); // idle | analyzing | analyzed | importing | done | error
  const [analysis, setAnalysis] = useState(null);
  const [result, setResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [sources, setSources] = useState([]);
  const [editMapping, setEditMapping] = useState({});
  const fileRef = useRef(null);

  const loadSources = async () => {
    try {
      const data = await getDataSources();
      setSources(Array.isArray(data) ? data : []);
    } catch {
      setSources([]);
    }
  };

  useEffect(() => {
    loadSources();
  }, []);

  // ─── Step 1: Select file → AI analyze ────────────────────────────────────
  const handleFileSelect = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;

    const allowed = ['.xlsx', '.xls', '.csv'];
    const ext = f.name.split('.').pop().toLowerCase();
    if (!allowed.includes('.' + ext)) {
      setErrorMsg('Поддерживаются только файлы Excel (.xlsx, .xls) и CSV (.csv)');
      return;
    }

    setFile(f);
    setAnalysis(null);
    setResult(null);
    setErrorMsg('');
    setStep('analyzing');

    try {
      const res = await analyzeExcelWithAI(f);
      if (!res.success) {
        setErrorMsg(res.error || 'Ошибка анализа файла');
        setStep('error');
        return;
      }
      setAnalysis(res);
      // Initialize editable mapping from AI result
      setEditMapping(res.column_mapping || {});
      setStep('analyzed');
    } catch (err) {
      setErrorMsg(`Ошибка анализа: ${err.message}`);
      setStep('error');
    }
  };

  // ─── Step 2: Confirm → Import ─────────────────────────────────────────────
  const handleImport = async () => {
    if (!file) return;
    setStep('importing');
    setErrorMsg('');

    try {
      const res = await importFile(file, null, editMapping);
      setResult(res);
      setStep('done');
      await loadSources();
    } catch (err) {
      setErrorMsg(`Ошибка импорта: ${err.message}`);
      setStep('error');
    }
  };

  const handleReset = () => {
    setFile(null);
    setAnalysis(null);
    setResult(null);
    setErrorMsg('');
    setStep('idle');
    setEditMapping({});
    if (fileRef.current) fileRef.current.value = '';
  };

  const handleDeleteSource = async (id) => {
    if (!confirm('Вы уверены, что хотите удалить этот источник и все его данные (товары, остатки, продажи)? Это действие необратимо.')) return;
    try {
      await deleteDataSource(id);
      await loadSources();
      // Optional: show a small success message if needed, or just let it refresh.
    } catch (err) {
      setErrorMsg(`Ошибка удаления: ${err.message}`);
    }
  };

  // ─── Helpers ─────────────────────────────────────────────────────────────
  const qualityInfo = analysis?.file_quality
    ? QUALITY_LABELS[analysis.file_quality] || { label: analysis.file_quality, color: '#6b7280' }
    : null;

  const mappedColumns = analysis
    ? Object.entries(editMapping).filter(([, v]) => v)
    : [];

  const unmappedColumns = analysis
    ? Object.entries(editMapping).filter(([, v]) => !v)
    : [];

  return (
    <div style={{ padding: '24px', maxWidth: '800px', margin: '0 auto' }}>

      {/* ── Header ── */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '22px', fontWeight: '700', color: '#f1f5f9', margin: '0 0 4px' }}>
          Импорт данных
        </h1>
        <p style={{ color: '#94a3b8', margin: 0, fontSize: '14px' }}>
          Загрузите Excel или CSV — ИИ автоматически определит структуру файла
        </p>
      </div>

      {/* ── Drop zone / File selector ── */}
      {step === 'idle' || step === 'error' ? (
        <div
          onClick={() => fileRef.current?.click()}
          style={{
            border: '2px dashed rgba(99,102,241,0.5)',
            borderRadius: '12px',
            padding: '40px',
            textAlign: 'center',
            cursor: 'pointer',
            background: 'rgba(99,102,241,0.05)',
            transition: 'all 0.2s',
            marginBottom: '20px',
          }}
          onMouseEnter={e => e.currentTarget.style.borderColor = 'rgba(99,102,241,0.9)'}
          onMouseLeave={e => e.currentTarget.style.borderColor = 'rgba(99,102,241,0.5)'}
        >
          <div style={{ fontSize: '40px', marginBottom: '12px' }}>📂</div>
          <p style={{ color: '#c7d2fe', fontWeight: '600', fontSize: '16px', margin: '0 0 6px' }}>
            Выберите Excel или CSV файл
          </p>
          <p style={{ color: '#64748b', fontSize: '13px', margin: 0 }}>
            Поддерживаются: .xlsx, .xls, .csv
          </p>
          <input
            ref={fileRef}
            type="file"
            accept=".xlsx,.xls,.csv"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
        </div>
      ) : null}

      {/* ── Error ── */}
      {errorMsg && (
        <div style={{
          background: 'rgba(239,68,68,0.12)',
          border: '1px solid rgba(239,68,68,0.4)',
          borderRadius: '10px',
          padding: '14px 16px',
          marginBottom: '16px',
          display: 'flex',
          gap: '10px',
          alignItems: 'flex-start',
        }}>
          <span style={{ fontSize: '18px' }}>⚠️</span>
          <div>
            <p style={{ color: '#fca5a5', fontWeight: '600', margin: '0 0 4px', fontSize: '14px' }}>
              Ошибка
            </p>
            <p style={{ color: '#f87171', margin: 0, fontSize: '13px' }}>{errorMsg}</p>
          </div>
          <button
            onClick={handleReset}
            style={{
              marginLeft: 'auto', background: 'none', border: 'none',
              color: '#94a3b8', cursor: 'pointer', fontSize: '18px',
            }}
          >×</button>
        </div>
      )}

      {/* ── Analyzing spinner ── */}
      {step === 'analyzing' && (
        <div style={{
          background: 'rgba(99,102,241,0.08)',
          border: '1px solid rgba(99,102,241,0.3)',
          borderRadius: '12px',
          padding: '32px',
          textAlign: 'center',
          marginBottom: '20px',
        }}>
          <div style={{
            width: '40px', height: '40px',
            border: '3px solid rgba(99,102,241,0.3)',
            borderTop: '3px solid #818cf8',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
            margin: '0 auto 16px',
          }} />
          <p style={{ color: '#a5b4fc', fontWeight: '600', margin: '0 0 4px' }}>
            ИИ анализирует файл...
          </p>
          <p style={{ color: '#64748b', fontSize: '13px', margin: 0 }}>
            {file?.name}
          </p>
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      )}

      {/* ── Analysis result ── */}
      {step === 'analyzed' && analysis && (
        <div style={{ marginBottom: '20px' }}>

          {/* File info bar */}
          <div style={{
            background: 'rgba(30,41,59,0.7)',
            border: '1px solid rgba(148,163,184,0.15)',
            borderRadius: '10px',
            padding: '14px 16px',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
          }}>
            <span style={{ fontSize: '24px' }}>
              {file?.name?.endsWith('.csv') ? '📄' : '📊'}
            </span>
            <div style={{ flex: 1 }}>
              <p style={{ color: '#f1f5f9', fontWeight: '600', margin: '0 0 2px', fontSize: '14px' }}>
                {file?.name}
              </p>
              <p style={{ color: '#64748b', margin: 0, fontSize: '12px' }}>
                Найдено строк: <strong style={{ color: '#94a3b8' }}>{analysis.total_rows}</strong>
                &nbsp;&nbsp;|&nbsp;&nbsp;
                Качество:&nbsp;
                <strong style={{ color: qualityInfo?.color }}>
                  {qualityInfo?.label || analysis.file_quality}
                </strong>
                {analysis.source === 'ai'
                  ? <>&nbsp;&nbsp;|&nbsp;&nbsp;<span style={{ color: '#a5b4fc' }}>✨ ИИ-анализ</span></>
                  : <>&nbsp;&nbsp;|&nbsp;&nbsp;<span style={{ color: '#94a3b8' }}>Автоматическое определение</span></>
                }
              </p>
            </div>
            <button
              onClick={handleReset}
              style={{
                background: 'none', border: 'none', color: '#64748b',
                cursor: 'pointer', fontSize: '20px', padding: '4px',
              }}
            >×</button>
          </div>

          {/* AI summary */}
          {analysis.ai_summary && (
            <div style={{
              background: 'rgba(99,102,241,0.07)',
              border: '1px solid rgba(99,102,241,0.25)',
              borderRadius: '10px',
              padding: '14px 16px',
              marginBottom: '16px',
            }}>
              <p style={{ color: '#a5b4fc', fontSize: '13px', fontWeight: '600', margin: '0 0 4px' }}>
                ✨ Анализ ИИ
              </p>
              <p style={{ color: '#c7d2fe', fontSize: '14px', margin: 0 }}>
                {analysis.ai_summary}
              </p>
              {analysis.detected_categories?.length > 0 && (
                <p style={{ color: '#818cf8', fontSize: '12px', margin: '8px 0 0' }}>
                  Категории: {analysis.detected_categories.join(', ')}
                </p>
              )}
            </div>
          )}

          {/* Column mapping */}
          <div style={{
            background: 'rgba(30,41,59,0.6)',
            border: '1px solid rgba(148,163,184,0.12)',
            borderRadius: '10px',
            padding: '16px',
            marginBottom: '16px',
          }}>
            <p style={{ color: '#94a3b8', fontWeight: '600', fontSize: '13px', margin: '0 0 12px' }}>
              Сопоставление колонок
            </p>

            {mappedColumns.map(([header, field]) => (
              <div key={header} style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                marginBottom: '8px',
              }}>
                <span style={{
                  background: 'rgba(71,85,105,0.5)',
                  border: '1px solid rgba(148,163,184,0.15)',
                  borderRadius: '6px',
                  padding: '4px 10px',
                  fontSize: '13px',
                  color: '#cbd5e1',
                  minWidth: '160px',
                  fontFamily: 'monospace',
                }}>
                  {header}
                </span>
                <span style={{ color: '#475569', fontSize: '16px' }}>→</span>
                <select
                  value={field || ''}
                  onChange={e => setEditMapping(prev => ({ ...prev, [header]: e.target.value || null }))}
                  style={{
                    background: 'rgba(22,163,74,0.1)',
                    border: '1px solid rgba(22,163,74,0.35)',
                    borderRadius: '6px',
                    padding: '4px 8px',
                    fontSize: '13px',
                    color: '#86efac',
                    cursor: 'pointer',
                  }}
                >
                  <option value="">— не импортировать —</option>
                  {Object.entries(FIELD_LABELS).map(([f, l]) => (
                    <option key={f} value={f}>{l}</option>
                  ))}
                </select>
              </div>
            ))}

            {unmappedColumns.length > 0 && (
              <>
                <p style={{ color: '#475569', fontSize: '12px', margin: '12px 0 8px' }}>
                  Нераспознанные колонки:
                </p>
                {unmappedColumns.map(([header]) => (
                  <div key={header} style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    marginBottom: '8px',
                  }}>
                    <span style={{
                      background: 'rgba(71,85,105,0.3)',
                      border: '1px solid rgba(148,163,184,0.1)',
                      borderRadius: '6px',
                      padding: '4px 10px',
                      fontSize: '13px',
                      color: '#64748b',
                      minWidth: '160px',
                      fontFamily: 'monospace',
                    }}>
                      {header}
                    </span>
                    <span style={{ color: '#475569', fontSize: '16px' }}>→</span>
                    <select
                      value=""
                      onChange={e => {
                        if (e.target.value) {
                          setEditMapping(prev => ({ ...prev, [header]: e.target.value }));
                        }
                      }}
                      style={{
                        background: 'rgba(71,85,105,0.3)',
                        border: '1px solid rgba(71,85,105,0.4)',
                        borderRadius: '6px',
                        padding: '4px 8px',
                        fontSize: '13px',
                        color: '#64748b',
                        cursor: 'pointer',
                      }}
                    >
                      <option value="">— выбрать поле —</option>
                      {Object.entries(FIELD_LABELS).map(([f, l]) => (
                        <option key={f} value={f}>{l}</option>
                      ))}
                    </select>
                  </div>
                ))}
              </>
            )}
          </div>

          {/* Warnings */}
          {analysis.warnings?.length > 0 && (
            <div style={{
              background: 'rgba(245,158,11,0.08)',
              border: '1px solid rgba(245,158,11,0.3)',
              borderRadius: '10px',
              padding: '12px 14px',
              marginBottom: '16px',
            }}>
              <p style={{ color: '#fbbf24', fontWeight: '600', fontSize: '13px', margin: '0 0 6px' }}>
                ⚠️ Предупреждения
              </p>
              {analysis.warnings.map((w, i) => (
                <p key={i} style={{ color: '#fde68a', fontSize: '13px', margin: '0 0 2px' }}>
                  • {w}
                </p>
              ))}
            </div>
          )}

          {/* missing required */}
          {analysis.missing_required?.length > 0 && (
            <div style={{
              background: 'rgba(239,68,68,0.08)',
              border: '1px solid rgba(239,68,68,0.3)',
              borderRadius: '10px',
              padding: '12px 14px',
              marginBottom: '16px',
            }}>
              <p style={{ color: '#f87171', fontWeight: '600', fontSize: '13px', margin: '0 0 4px' }}>
                ❌ Не найдены обязательные поля: {analysis.missing_required.join(', ')}
              </p>
              <p style={{ color: '#fca5a5', fontSize: '12px', margin: 0 }}>
                Назначьте поля вручную выше или проверьте файл.
              </p>
            </div>
          )}

          {/* Confirm button */}
          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              onClick={handleImport}
              disabled={analysis.missing_required?.includes('name') &&
                !Object.values(editMapping).includes('name')}
              style={{
                flex: 1,
                padding: '12px 24px',
                background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                border: 'none',
                borderRadius: '10px',
                color: '#fff',
                fontWeight: '700',
                fontSize: '15px',
                cursor: 'pointer',
                opacity: (analysis.missing_required?.includes('name') &&
                  !Object.values(editMapping).includes('name')) ? 0.5 : 1,
              }}
            >
              ✅ Подтвердить импорт ({analysis.total_rows} строк)
            </button>
            <button
              onClick={handleReset}
              style={{
                padding: '12px 20px',
                background: 'rgba(71,85,105,0.4)',
                border: '1px solid rgba(148,163,184,0.2)',
                borderRadius: '10px',
                color: '#94a3b8',
                fontWeight: '600',
                cursor: 'pointer',
              }}
            >
              Отмена
            </button>
          </div>
        </div>
      )}

      {/* ── Importing spinner ── */}
      {step === 'importing' && (
        <div style={{
          background: 'rgba(99,102,241,0.08)',
          border: '1px solid rgba(99,102,241,0.3)',
          borderRadius: '12px',
          padding: '32px',
          textAlign: 'center',
          marginBottom: '20px',
        }}>
          <div style={{
            width: '40px', height: '40px',
            border: '3px solid rgba(99,102,241,0.3)',
            borderTop: '3px solid #818cf8',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
            margin: '0 auto 16px',
          }} />
          <p style={{ color: '#a5b4fc', fontWeight: '600', margin: '0 0 4px' }}>
            Импорт выполняется...
          </p>
          <p style={{ color: '#64748b', fontSize: '13px', margin: 0 }}>
            Товары записываются в базу данных
          </p>
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      )}

      {/* ── Import result ── */}
      {step === 'done' && result && (
        <div style={{
          background: result.success ? 'rgba(22,163,74,0.08)' : 'rgba(239,68,68,0.08)',
          border: `1px solid ${result.success ? 'rgba(22,163,74,0.35)' : 'rgba(239,68,68,0.35)'}`,
          borderRadius: '12px',
          padding: '20px',
          marginBottom: '20px',
        }}>
          <p style={{
            color: result.success ? '#86efac' : '#f87171',
            fontWeight: '700',
            fontSize: '16px',
            margin: '0 0 12px',
          }}>
            {result.success ? '✅ Импорт завершён' : '❌ Ошибка импорта'}
          </p>

          {result.success ? (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px', marginBottom: '12px' }}>
              {[
                { label: 'Импортировано', value: result.products_imported, color: '#22c55e' },
                { label: 'Обновлено', value: result.products_updated, color: '#3b82f6' },
                { label: 'Ошибок', value: result.error_count || 0, color: '#f59e0b' },
              ].map(({ label, value, color }) => (
                <div key={label} style={{
                  background: 'rgba(30,41,59,0.6)',
                  borderRadius: '8px',
                  padding: '12px',
                  textAlign: 'center',
                }}>
                  <p style={{ color, fontSize: '24px', fontWeight: '700', margin: '0 0 4px' }}>
                    {value}
                  </p>
                  <p style={{ color: '#64748b', fontSize: '12px', margin: 0 }}>{label}</p>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: '#fca5a5', margin: '0 0 12px', fontSize: '14px' }}>
              {result.message}
            </p>
          )}

          {result.errors?.length > 0 && (
            <details style={{ marginBottom: '12px' }}>
              <summary style={{ color: '#f59e0b', cursor: 'pointer', fontSize: '13px', marginBottom: '6px' }}>
                Строки с ошибками ({result.errors.length})
              </summary>
              <div style={{
                background: 'rgba(0,0,0,0.2)',
                borderRadius: '6px',
                padding: '10px',
                maxHeight: '200px',
                overflow: 'auto',
              }}>
                {result.errors.map((e, i) => (
                  <p key={i} style={{ color: '#fca5a5', fontSize: '12px', margin: '0 0 4px', fontFamily: 'monospace' }}>
                    Строка {e.row}: {e.error}
                  </p>
                ))}
              </div>
            </details>
          )}

          <button
            onClick={handleReset}
            style={{
              padding: '10px 20px',
              background: 'rgba(99,102,241,0.3)',
              border: '1px solid rgba(99,102,241,0.5)',
              borderRadius: '8px',
              color: '#a5b4fc',
              fontWeight: '600',
              cursor: 'pointer',
              fontSize: '14px',
            }}
          >
            Загрузить другой файл
          </button>
        </div>
      )}

      {/* ── Data sources ── */}
      {sources.length > 0 && (
        <div style={{
          background: 'rgba(30,41,59,0.5)',
          border: '1px solid rgba(148,163,184,0.1)',
          borderRadius: '10px',
          padding: '16px',
        }}>
          <p style={{ color: '#64748b', fontWeight: '600', fontSize: '13px', margin: '0 0 10px' }}>
            Источники данных
          </p>
          {sources.map(s => (
            <div key={s.id} style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '8px 0',
              borderBottom: '1px solid rgba(148,163,184,0.08)',
            }}>
              <div>
                <span style={{ color: '#cbd5e1', fontSize: '14px', fontWeight: '500' }}>
                  {s.name}
                </span>
                <span style={{
                  marginLeft: '8px',
                  background: s.status === 'active' ? 'rgba(22,163,74,0.2)' : 'rgba(71,85,105,0.3)',
                  color: s.status === 'active' ? '#86efac' : '#94a3b8',
                  borderRadius: '4px',
                  padding: '2px 8px',
                  fontSize: '11px',
                }}>
                  {s.status === 'active' ? 'Активен' : s.status}
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <div style={{ textAlign: 'right' }}>
                  <p style={{ color: '#94a3b8', fontSize: '12px', margin: '0 0 2px' }}>
                    {s.records_imported || 0} записей
                  </p>
                  {s.last_sync && (
                    <p style={{ color: '#475569', fontSize: '11px', margin: 0 }}>
                      Синхронизация: {new Date(s.last_sync).toLocaleString('ru-RU')}
                    </p>
                  )}
                </div>
                <button
                  onClick={() => handleDeleteSource(s.id)}
                  title="Удалить источник и данные"
                  style={{
                    background: 'rgba(239,68,68,0.1)',
                    border: '1px solid rgba(239,68,68,0.3)',
                    color: '#f87171',
                    borderRadius: '6px',
                    padding: '6px 10px',
                    cursor: 'pointer',
                    fontSize: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'all 0.2s',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'rgba(239,68,68,0.2)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'rgba(239,68,68,0.1)'}
                >
                  🗑️ Удалить
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
