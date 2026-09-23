'use client';
/**
 * ScanIZI — Auth Context
 */
import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { login as apiLogin, getMe } from '@/lib/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const checkAuth = useCallback(async () => {
    const token = localStorage.getItem('scanizi_token');
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await getMe();
      setUser(me);
      localStorage.setItem('scanizi_user', JSON.stringify(me));
    } catch {
      localStorage.removeItem('scanizi_token');
      localStorage.removeItem('scanizi_user');
      setUser(null);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = async (username, password) => {
    setError(null);
    try {
      await apiLogin(username, password);
      const me = await getMe();
      setUser(me);
      localStorage.setItem('scanizi_user', JSON.stringify(me));
      return true;
    } catch (err) {
      setError(err.message || 'Ошибка входа');
      return false;
    }
  };

  const logout = () => {
    localStorage.removeItem('scanizi_token');
    localStorage.removeItem('scanizi_user');
    setUser(null);
  };

  const isOwner = user?.role === 'owner';
  const isManager = user?.role === 'manager' || isOwner;

  return (
    <AuthContext.Provider value={{ user, loading, error, login, logout, isOwner, isManager, setError }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be inside AuthProvider');
  return ctx;
}
