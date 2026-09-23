'use client';
/**
 * ScanIZI — Dashboard layout (sidebar + content area)
 * The Sidebar component now renders the mobile-topbar internally,
 * so this layout only needs the standard flex container.
 */
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import Sidebar from '@/components/Sidebar';

export default function DashboardLayout({ children }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace('/login');
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="loading-page">
        <div className="spinner" />
        <p className="text-muted">Загрузка...</p>
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-content">
        {children}
      </main>
    </div>
  );
}
