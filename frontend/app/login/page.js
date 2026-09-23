'use client';
/**
 * ScanIZI — Login page
 */
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { ScanBarcode } from 'lucide-react';

export default function LoginPage() {
  const { user, loading, login, error, setError } = useAuth();
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!loading && user) router.replace('/dashboard');
  }, [user, loading, router]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username || !password) {
      setError('Введите логин и пароль');
      return;
    }
    setSubmitting(true);
    const ok = await login(username, password);
    if (ok) router.replace('/dashboard');
    setSubmitting(false);
  };

  if (loading) {
    return (
      <div className="loading-page">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-logo">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <ScanBarcode size={32} style={{ color: 'var(--primary-400)' }} />
          </div>
          <h1>ScanIZI</h1>
          <p>Интеллектуальный анализ товаров и запасов</p>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          {error && <div className="login-error">{error}</div>}

          <div className="input-group">
            <label className="input-label">Логин</label>
            <input
              className="input"
              type="text"
              placeholder="admin"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              autoFocus
            />
          </div>

          <div className="input-group">
            <label className="input-label">Пароль</label>
            <input
              className="input"
              type="password"
              placeholder="••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={submitting}
            style={{ width: '100%', padding: '0.75rem' }}
          >
            {submitting ? 'Вход...' : 'Войти в систему'}
          </button>

          <div style={{ textAlign: 'center', marginTop: '0.5rem' }}>
            <p className="text-muted" style={{ fontSize: '0.75rem' }}>
              Демо-доступ: admin / admin
            </p>
          </div>
        </form>
      </div>
    </div>
  );
}
