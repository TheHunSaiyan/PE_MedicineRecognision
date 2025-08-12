"use client";

import { createContext, useContext, useState, ReactNode, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { jwtDecode } from 'jwt-decode';

interface UserData {
  role: string;
  sub: string;
  exp: number;
}

interface AuthContextType {
  isAuthenticated: boolean;
  userRole: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  token: string | null;
  hasRole: (requiredRole: string) => boolean;
  hasAnyRole: (allowedRoles: string[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [userRole, setUserRole] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const checkAuth = async () => {
  const storedToken = localStorage.getItem('token');
  
  if (storedToken) {
    try {
      if (isTokenExpired(storedToken)) {
        logout();
        return;
      }
      
      const decoded: UserData = jwtDecode(storedToken);
      setToken(storedToken);
      setUserRole(decoded.role);
      setIsAuthenticated(true);
    } catch (error) {
      console.error("Invalid token:", error);
      logout();
    }
  }
  setIsLoading(false);
};
    checkAuth();
  }, []);

  const isTokenExpired = (token: string): boolean => {
  try {
    const decoded: UserData = jwtDecode(token);
    return decoded.exp * 1000 < Date.now();
  } catch (error) {
    return true;
  }
};

  const login = async (email: string, password: string) => {
    try {
      const response = await fetch('http://localhost:2076/attempt_login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({ email, password }),
    });

      const data = await response.json();

      if (response.ok) {
        localStorage.setItem('token', data.token);
        const decoded: UserData = jwtDecode(data.token);
        setToken(data.token);
        setUserRole(decoded.role);
        setIsAuthenticated(true);
        
        router.push('/mainpage');
      } else {
        throw new Error(data.detail || 'Login failed');
      }
    } catch (err) {
      throw err;
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUserRole(null);
    setIsAuthenticated(false);
    router.push('/login');
  };

  if (isLoading) {
    return <div>Loading...</div>;
  }

    const hasRole = (requiredRole: string) => {
    return userRole === requiredRole;
  };

  const hasAnyRole = (allowedRoles: string[]) => {
  if (!userRole) return false;
  return allowedRoles.includes(userRole);
};

  return (
    <AuthContext.Provider value={{ isAuthenticated, userRole, login, logout, token, hasRole, hasAnyRole }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};