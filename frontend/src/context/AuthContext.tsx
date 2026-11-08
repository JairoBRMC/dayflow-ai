import { useEffect, useState, type ReactNode } from "react";
import { fetchCurrentUser, loginRequest, registerRequest, type AuthUser } from "../api/auth";
import { AuthContext } from "./auth-context";

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<AuthUser | null>(null);
    // Estado inicial perezoso: si no hay token guardado, no hay nada que esperar.
    const [isLoading, setIsLoading] = useState(() => Boolean(localStorage.getItem("access_token")));

    useEffect(() => {
        if (!localStorage.getItem("access_token")) {
            return;
        }

        // Si el access_token guardado ya expiró, el interceptor de client.ts lo
        // renueva solo con el refresh_token antes de que esta llamada falle.
        fetchCurrentUser()
            .then(setUser)
            .catch(() => {
                localStorage.removeItem("access_token");
                localStorage.removeItem("refresh_token");
            })
            .finally(() => setIsLoading(false));
    }, []);

    async function login(email: string, password: string) {
        const tokens = await loginRequest(email, password);
        localStorage.setItem("access_token", tokens.access_token);
        localStorage.setItem("refresh_token", tokens.refresh_token);
        setUser(await fetchCurrentUser());
    }

    async function register(email: string, password: string) {
        // POST /auth/register no devuelve tokens, solo crea el usuario -- se
        // encadena un login para no obligar a teclear las credenciales dos veces.
        await registerRequest(email, password);
        await login(email, password);
    }

    function logout() {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        setUser(null);
    }

    return (
        <AuthContext.Provider value={{ user, isLoading, login, register, logout }}>
            {children}
        </AuthContext.Provider>
    );
}
