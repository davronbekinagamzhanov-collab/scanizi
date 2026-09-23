'use client';
import { useState, useEffect } from 'react';
import { getEmployees, createEmployee } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { Users, Plus, Shield, UserCheck } from 'lucide-react';

export default function EmployeesPage() {
  const { isOwner, isManager } = useAuth();
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ full_name: '', username: '', password: '', role: 'employee' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const fetchEmployees = () => {
    setLoading(true);
    getEmployees().then(setEmployees).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { fetchEmployees(); }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!form.full_name || !form.username || !form.password) { setError('Заполните все поля'); return; }
    setSaving(true);
    try {
      await createEmployee(form);
      setShowForm(false);
      setForm({ full_name: '', username: '', password: '', role: 'employee' });
      fetchEmployees();
    } catch (err) { setError(err.message); }
    setSaving(false);
  };

  const roleIcon = { owner: Shield, manager: UserCheck, employee: Users };
  const roleLabel = { owner: 'Владелец', manager: 'Управляющий', employee: 'Сотрудник' };

  if (loading) return <div className="loading-page"><div className="spinner" /></div>;

  return (
    <>
      <div className="page-header">
        <div className="page-title-group">
          <h1 className="page-title">Сотрудники</h1>
          <p className="page-subtitle">{employees.length} пользователей</p>
        </div>
        {isOwner && <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}><Plus size={16} /> Добавить</button>}
      </div>
      <div className="page-content">
        {showForm && (
          <div className="card" style={{ marginBottom: '1.5rem', maxWidth: 500 }}>
            <h3 style={{ marginBottom: '1rem' }}>Новый сотрудник</h3>
            {error && <div className="login-error" style={{ marginBottom: '0.75rem' }}>{error}</div>}
            <form onSubmit={handleCreate} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div className="input-group"><label className="input-label">ФИО</label><input className="input" value={form.full_name} onChange={e => setForm(f => ({...f, full_name: e.target.value}))} /></div>
              <div className="input-group"><label className="input-label">Логин</label><input className="input" value={form.username} onChange={e => setForm(f => ({...f, username: e.target.value}))} /></div>
              <div className="input-group"><label className="input-label">Пароль</label><input className="input" type="password" value={form.password} onChange={e => setForm(f => ({...f, password: e.target.value}))} /></div>
              <div className="input-group">
                <label className="input-label">Роль</label>
                <select className="input" value={form.role} onChange={e => setForm(f => ({...f, role: e.target.value}))}>
                  <option value="employee">Сотрудник</option>
                  <option value="manager">Управляющий</option>
                </select>
              </div>
              <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? 'Создание...' : 'Создать'}</button>
            </form>
          </div>
        )}

        <div className="table-container">
          <table>
            <thead><tr><th>ФИО</th><th>Логин</th><th>Роль</th><th>Статус</th></tr></thead>
            <tbody>
              {employees.map(emp => {
                const RoleIcon = roleIcon[emp.role] || Users;
                return (
                  <tr key={emp.id}>
                    <td style={{ fontWeight: 500 }}>{emp.full_name}</td>
                    <td style={{ fontFamily: 'monospace' }}>{emp.username}</td>
                    <td><span className="badge badge-primary" style={{ display: 'inline-flex', gap: 4 }}><RoleIcon size={12} />{roleLabel[emp.role]}</span></td>
                    <td><span className={`badge ${emp.is_active ? 'badge-success' : 'badge-danger'}`}>{emp.is_active ? 'Активен' : 'Отключён'}</span></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
