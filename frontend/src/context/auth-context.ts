import { createContext } from "react";
import type { AuthUser } from "../api/auth";

export interface AuthContextValue {
    user: AuthUser | null;
    // true mientras se comprueba si el access_token guardado sigue siendo válido;
    // evita que ProtectedRoute redirija a /login antes de saberlo de verdad.
    isLoading: boolean;
    login: (email: string, password: string) => Promise<void>;
    register: (email: string, password: string) => Promise<void>;
    logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);
