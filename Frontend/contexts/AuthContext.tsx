"use client";

import { createContext, useContext, useState, ReactNode, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Role } from '../constans/roles';


interface AuthContextType {
  isAuthenticated: boolean;
  userRole: Role | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  hasRole: (requiredRole: string) => boolean;
  hasAnyRole: (allowedRoles: string[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userRole, setUserRole] = useState<Role | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const response = await fetch('http://localhost:2076/check_session', {
          credentials: 'include',
        });
        
        if (response.ok) {
          const data = await response.json();
          setIsAuthenticated(true);
          setUserRole(data.role as Role);
        }
      } catch (error) {
        console.error("Session check failed:", error);
      } finally {
        setIsLoading(false);
      }
    };
    
    checkAuth();
  }, []);

  const login = async (email: string, password: string) => {
    try {
      const response = await fetch('http://localhost:2076/attempt_login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({ email, password }),
    });

      const data = await response.json();

      if (response.ok) {
        setUserRole(data.role as Role);
        setIsAuthenticated(true);
      } else {
        throw new Error(data.detail || 'Login failed');
      }
    } catch (err) {
      throw err;
    }
  };

  const logout = async () => {
    try {
      await fetch('http://localhost:2076/logout', {
        method: 'POST',
        credentials: 'include',
      });
    } finally {
      setIsAuthenticated(false);
      setUserRole(null);
      router.push('/login');
    }
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
    <AuthContext.Provider value={{ isAuthenticated, userRole, login, logout, hasRole, hasAnyRole }}>
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