import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Initialize auth state on mount
  useEffect(() => {
    async function loadUser() {
      const token = localStorage.getItem('brightloop_token');
      if (!token) {
        setLoading(false);
        return;
      }

      try {
        const response = await api.getMe();
        setUser(response.user);
      } catch (err) {
        console.warn('Authentication token expired or invalid:', err.message);
        localStorage.removeItem('brightloop_token');
        setUser(null);
      } finally {
        setLoading(false);
      }
    }

    loadUser();
  }, []);

  const login = async (credentials) => {
    const data = await api.login(credentials);
    localStorage.setItem('brightloop_token', data.token);
    setUser(data.user);
    
    // Output requirement:
    // Admin goes to Admin Dashboard.
    // Customer goes to Customer Dashboard.
    const redirectPath = data.user.role === 'admin' 
      ? '/admin-dashboard' 
      : '/customer-dashboard';
    
    return { user: data.user, redirectPath };
  };

  const registerCustomer = async (customerData) => {
    const data = await api.registerCustomer(customerData);
    localStorage.setItem('brightloop_token', data.token);
    setUser(data.user);
    return { user: data.user, redirectPath: '/customer-dashboard' };
  };

  const logout = () => {
    localStorage.removeItem('brightloop_token');
    setUser(null);
  };

  const updateUser = (updatedProfile) => {
    setUser(prev => prev ? { ...prev, profile: { ...prev.profile, ...updatedProfile } } : null);
  };

  return (
    <AuthContext.Provider value={{
      user,
      loading,
      login,
      registerCustomer,
      logout,
      updateUser,
      isAuthenticated: !!user,
      isAdmin: user?.role === 'admin',
      isCustomer: user?.role === 'customer',
      isStaff: user?.role === 'staff'
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
