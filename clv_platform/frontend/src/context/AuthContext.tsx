import React, { createContext, useContext, useState, useEffect } from 'react';

interface UserInfo {
  email: string;
  role: string;
  tenantId: number | null;
}

interface AuthContextType {
  token: string | null;
  user: UserInfo | null;
  isAuthenticated: boolean;
  login: (email: string, role: string, tenantId: number | null, token: string) => void;
  logout: () => void;
  apiCall: (endpoint: string, options?: RequestInit) => Promise<any>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(localStorage.getItem('clv_jwt_token'));
  const [user, setUser] = useState<UserInfo | null>(null);

  useEffect(() => {
    const cachedUser = localStorage.getItem('clv_user_info');
    if (token && cachedUser) {
      setUser(JSON.parse(cachedUser));
    }
  }, [token]);

  const login = (email: string, role: string, tenantId: number | null, token: string) => {
    localStorage.setItem('clv_jwt_token', token);
    const userInfo = { email, role, tenantId };
    localStorage.setItem('clv_user_info', JSON.stringify(userInfo));
    setToken(token);
    setUser(userInfo);
  };

  const logout = () => {
    localStorage.removeItem('clv_jwt_token');
    localStorage.removeItem('clv_user_info');
    setToken(null);
    setUser(null);
  };

  const apiCall = async (endpoint: string, options: RequestInit = {}) => {
    const headers = new Headers(options.headers || {});
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
    
    const response = await fetch(endpoint, {
      ...options,
      headers
    });
    
    if (response.status === 401) {
      logout();
      throw new Error('Session expired. Please log in again.');
    }
    
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Unknown error occurred' }));
      throw new Error(err.detail || 'Request failed');
    }
    
    // Check if zip, excel or pdf download
    const contentType = response.headers.get('Content-Type') || '';
    if (contentType.includes('application/pdf') || contentType.includes('application/vnd.openxmlformats')) {
      return response.blob();
    }
    
    return response.json();
  };

  return (
    <AuthContext.Provider value={{
      token,
      user,
      isAuthenticated: !!token,
      login,
      logout,
      apiCall
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
