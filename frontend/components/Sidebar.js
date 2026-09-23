'use client';
/**
 * ScanIZI — Sidebar navigation component
 * Mobile-first robust architecture: no z-index wars, proper overlay, smooth animation.
 */
import { useState, useEffect, useCallback } from 'react';
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

  // Close sidebar when navigating on mobile
  const closeMobile = useCallback(() => setMobileOpen(false), []);

  // Close on Escape key
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape' && mobileOpen) closeMobile();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [mobileOpen, closeMobile]);

  // Prevent body scroll when mobile menu is open
  useEffect(() => {
    if (mobileOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => { document.body.style.overflow = ''; };
  }, [mobileOpen]);

  const filteredItems = NAV_ITEMS.filter(item => {
    if (item.section) return true;
    if (item.ownerOnly && !isOwner) return false;
    if (item.managerOnly && !isManager) return false;
    return true;
  });

  // Collapse empty sections (sections with no visible items under them)
  const visibleItems = [];
  for (let i = 0; i < filteredItems.length; i++) {
    const item = filteredItems[i];
    if (item.section) {
      // Check if any non-section item follows before next section
      const hasChildren = filteredItems.slice(i + 1).some(
        (next) => !next.section
      );
      if (hasChildren) visibleItems.push(item);
    } else {
      visibleItems.push(item);
    }
  }

  const initials = user?.full_name
    ? user.full_name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
    : (user?.username || 'U').slice(0, 2).toUpperCase();

  const roleLabel = {
    owner: 'Владелец',
    manager: 'Управляющий',
    employee: 'Сотрудник',
  };

  return (
    <>
      {/* ─── Mobile header bar ──────────────────────────────
          Lives inside the normal document flow at the top of main-content.
          Does NOT use position:fixed so it cannot overlap page-header icons.
      ──────────────────────────────────────────────────── */}
      <div className="mobile-topbar" aria-hidden={!mobileOpen ? undefined : 'false'}>
        <button
          className="mobile-burger"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label={mobileOpen ? 'Закрыть меню' : 'Открыть меню'}
          aria-expanded={mobileOpen}
          aria-controls="sidebar-nav"
        >
          {mobileOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
        <div className="mobile-logo">
          <div className="logo-icon" style={{ width: 28, height: 28, fontSize: '0.75rem' }}>Si</div>
          <span style={{ fontWeight: 800, fontSize: '1rem', background: 'linear-gradient(135deg, var(--primary-400), var(--accent-400))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>ScanIZI</span>
        </div>
      </div>

      {/* ─── Overlay ─────────────────────────────────────── */}
      <div
        className={`mobile-overlay${mobileOpen ? ' visible' : ''}`}
        onClick={closeMobile}
        aria-hidden="true"
      />

      {/* ─── Sidebar ─────────────────────────────────────── */}
      <aside
        id="sidebar-nav"
        className={`sidebar${mobileOpen ? ' open' : ''}`}
        aria-label="Навигация"
      >
        {/* Desktop logo */}
        <div className="sidebar-logo">
          <div className="logo-icon">Si</div>
          <h1>ScanIZI</h1>
        </div>

        <nav className="sidebar-nav">
          {visibleItems.map((item, i) => {
            if (item.section) {
              return <div key={`sec-${i}`} className="nav-section-title">{item.section}</div>;
            }
            const Icon = item.icon;
            const isActive = pathname === item.href ||
              (item.href !== '/dashboard' && pathname?.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`nav-link${isActive ? ' active' : ''}`}
                onClick={closeMobile}
                aria-current={isActive ? 'page' : undefined}
              >
                <Icon size={20} className="icon" aria-hidden="true" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <div className="user-info">
            <div className="user-avatar" aria-hidden="true">{initials}</div>
            <div className="user-details">
              <div className="user-name">{user?.full_name || user?.username || 'Пользователь'}</div>
              <div className="user-role">{roleLabel[user?.role] || user?.role}</div>
            </div>
            <button
              className="btn-ghost"
              onClick={logout}
              title="Выйти из системы"
              aria-label="Выйти из системы"
            >
              <LogOut size={18} aria-hidden="true" />
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
