'use client';
import { Info, Code, Shield, BrainCircuit, Database, BarChart3, Zap } from 'lucide-react';

export default function AboutPage() {
  return (
    <>
      <div className="page-header">
        <div className="page-title-group">
          <h1 className="page-title">О системе</h1>
          <p className="page-subtitle">ScanIZI — Интеллектуальный анализ товаров и запасов</p>
        </div>
      </div>
      <div className="page-content">
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <div style={{ textAlign: 'center', padding: '2rem 0 1rem' }}>
            <h1 style={{ fontSize: '2.5rem', fontWeight: 800, background: 'linear-gradient(135deg, var(--primary-400), var(--accent-400))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', marginBottom: '0.5rem' }}>ScanIZI</h1>
            <p className="text-secondary" style={{ fontSize: '1rem', maxWidth: 500, margin: '0 auto', lineHeight: 1.6 }}>
              Система помогает владельцам бизнеса в Узбекистане и Казахстане принимать обоснованные решения по управлению запасами с помощью AI-аналитики.
            </p>
            <span className="badge badge-primary" style={{ marginTop: '1rem', padding: '0.375rem 1rem' }}>v1.0.0 MVP</span>
          </div>
        </div>

        <div className="grid-3">
          {[
            { icon: BarChart3, title: 'Analytics Engine', desc: 'Все метрики рассчитываются Python/Pandas/NumPy — без hardcoded данных.' },
            { icon: BrainCircuit, title: 'AI Layer', desc: 'Google Gemini API для интеллектуальных рекомендаций. При отсутствии ключа — честный fallback.' },
            { icon: Zap, title: 'Decision Engine', desc: 'Multi-factor Risk Scoring + Impact/Priority Ranking для каждого товара.' },
            { icon: Database, title: 'Data Layer', desc: 'PostgreSQL + Data Normalization Layer для разных источников (Excel, CSV, GBS, 1C, UMAG).' },
            { icon: Shield, title: 'Auth & RBAC', desc: 'JWT + bcrypt + ролевая модель (owner → manager → employee).' },
            { icon: Code, title: 'Tech Stack', desc: 'FastAPI + SQLAlchemy | Next.js + Recharts | Docker Compose.' },
          ].map((item, i) => {
            const Icon = item.icon;
            return (
              <div className="card" key={i}>
                <Icon size={24} style={{ color: 'var(--primary-400)', marginBottom: '0.75rem' }} />
                <h4 style={{ marginBottom: '0.5rem' }}>{item.title}</h4>
                <p className="text-secondary" style={{ fontSize: '0.8125rem', lineHeight: 1.5 }}>{item.desc}</p>
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}
