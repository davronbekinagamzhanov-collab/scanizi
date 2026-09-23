'use client';
import { useAuth } from '@/lib/auth';
import { Settings as SettingsIcon, User, Bell, Globe } from 'lucide-react';

export default function SettingsPage() {
  const { user } = useAuth();

  return (
    <>
      <div className="page-header">
        <div className="page-title-group">
          <h1 className="page-title">Настройки</h1>
          <p className="page-subtitle">Параметры системы и профиля</p>
        </div>
      </div>
      <div className="page-content">
        <div className="grid-2">
          <div className="card">
            <div className="card-header"><span className="card-title"><User size={14} style={{ display: 'inline', marginRight: 6, verticalAlign: -2 }} />Профиль</span></div>
            <div style={{ display: 'grid', gap: '0.5rem', fontSize: '0.875rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span className="text-muted">ФИО</span><span>{user?.full_name}</span></div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span className="text-muted">Логин</span><span style={{ fontFamily: 'monospace' }}>{user?.username}</span></div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span className="text-muted">Роль</span><span>{user?.role}</span></div>
            </div>
          </div>
          <div className="card">
            <div className="card-header"><span className="card-title"><Globe size={14} style={{ display: 'inline', marginRight: 6, verticalAlign: -2 }} />Система</span></div>
            <div style={{ display: 'grid', gap: '0.5rem', fontSize: '0.875rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span className="text-muted">Валюта</span><span>KZT (₸)</span></div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span className="text-muted">Язык</span><span>Русский</span></div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span className="text-muted">Тема</span><span>Тёмная</span></div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span className="text-muted">API Backend</span><span style={{ fontFamily: 'monospace' }}>localhost:8000</span></div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
