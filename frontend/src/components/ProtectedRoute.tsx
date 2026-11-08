import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/useAuth";

export function ProtectedRoute({ children }: { children: ReactNode }) {
    const { user, isLoading } = useAuth();

    if (isLoading) {
        return <p className="auth-loading">Cargando...</p>;
    }

    if (!user) {
        return <Navigate to="/login" replace />;
    }

    return <>{children}</>;
}
