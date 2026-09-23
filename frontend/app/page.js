'use client';
/**
 * ScanIZI — Landing / Login redirect
 */
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';

export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading) {
      if (user) router.replace('/dashboard');
      else router.replace('/login');
    }
  }, [user, loading, router]);

  return (
    <div className="loading-page">
      <div className="spinner" />
      <p className="text-muted">Загрузка ScanIZI...</p>
    </div>
  );
}
