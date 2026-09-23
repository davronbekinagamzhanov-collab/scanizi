'use client';
/**
 * ScanIZI — Sidebar navigation component
 */
import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import {
  LayoutDashboard, Package, TrendingUp, Warehouse, DollarSign,
  Users, ScanBarcode, Database, Settings, Info, LogOut, Menu, X,
  BrainCircuit
} from 'lucide-react';

const NAV_ITEMS = [
  { section: 'Основное' },
  { href: '/dashboard', label: 'Обзор', icon: LayoutDashboard },
  { href: '/dashboard/products', label: 'Товары', icon: Package },
  { href: '/dashboard/sales', label: 'Продажи', icon: TrendingUp },
  { href: '/dashboard/capital', label: 'Капитал', icon: DollarSign, ownerOnly: true },
  { section: 'Операции' },
  { href: '/dashboard/warehouses', label: 'Склады', icon: Warehouse },
  { href: '/dashboard/scanner', label: 'Сканер', icon: ScanBarcode },
  { href: '/dashboard/recommendations', label: 'AI Рекомендации', icon: BrainCircuit },
  { section: 'Управление' },
  { href: '/dashboard/employees', label: 'Сотрудники', icon: Users, managerOnly: true },
  { href: '/dashboard/data', label: 'Данные', icon: Database, ownerOnly: true },
  { href: '/dashboard/settings', label: 'Настройки', icon: Settings },
  { href: '/dashboard/about', label: 'О системе', icon: Info },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout, isOwner, isManager } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  const filteredItems = NAV_ITEMS.filter(item => {
    if (item.section) return true;
    if (item.ownerOnly && !isOwner) return false;
    if (item.managerOnly && !isManager) return false;
    return true;
  });

  const initials = user?.full_name
    ? user.full_name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
    : 'U';

  const roleLabel = {
    owner: 'Владелец',
    manager: 'Управляющий',
    employee: 'Сотрудник',
  };

  return (
    <>
      {/* Mobile button */}
      <button
        className="mobile-menu-btn"
        onClick={() => setMobileOpen(!mobileOpen)}
        style={{ position: 'fixed', top: 16, left: 16, zIndex: 200 }}
      >
        {mobileOpen ? <X size={24} /> : <Menu size={24} />}
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="mobile-overlay visible" onClick={() => setMobileOpen(false)} />
      )}

      {/* Sidebar */}
      <aside className={`sidebar ${mobileOpen ? 'open' : ''}`}>
        <div className="sidebar-logo">
          <div className="logo-icon">Si</div>
          <h1>ScanIZI</h1>
        </div>

        <nav className="sidebar-nav">
          {filteredItems.map((item, i) => {
            if (item.section) {
              return <div key={i} className="nav-section-title">{item.section}</div>;
            }
            const Icon = item.icon;
            const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname?.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`nav-link ${isActive ? 'active' : ''}`}
                onClick={() => setMobileOpen(false)}
              >
                <Icon size={20} className="icon" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <div className="user-info">
            <div className="user-avatar">{initials}</div>
            <div className="user-details">
              <div className="user-name">{user?.full_name || 'User'}</div>
              <div className="user-role">{roleLabel[user?.role] || user?.role}</div>
            </div>
            <button className="btn-ghost" onClick={logout} title="Выйти">
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
