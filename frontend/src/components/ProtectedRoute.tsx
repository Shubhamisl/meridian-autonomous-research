import { Navigate } from 'react-router-dom';
import { type ReactNode } from 'react';
import { useAuth } from '../contexts/useAuth';

export default function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-ivory">
        <div className="rounded-full border border-fog/70 bg-white px-5 py-3 text-sm text-slate/65 shadow-soft">
          Loading workspace…
        </div>
      </div>
    );
  }

  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}
