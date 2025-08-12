"use client";

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';

export default function ProtectedRoute({ children, allowedRoles }: { children: React.ReactNode, allowedRoles?: string[] }) {
  const { isAuthenticated, userRole, hasAnyRole } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
    } else if (allowedRoles && !hasAnyRole(allowedRoles)) {
      router.push('/unauthorized');
    }
  }, [isAuthenticated, allowedRoles, hasAnyRole, router]);

  if (!isAuthenticated || (allowedRoles && !hasAnyRole(allowedRoles))) {
    return null;
  }

  return <>{children}</>;
}