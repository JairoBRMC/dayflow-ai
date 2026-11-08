import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../context/useAuth";
import "./AuthPages.css";

export function LoginPage() {
    const { login, user } = useAuth();
    const navigate = useNavigate();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    async function handleSubmit(event: FormEvent) {
        event.preventDefault();
        setError(null);
        setIsSubmitting(true);
        try {
            await login(email, password);
            navigate("/", { replace: true });
        } catch {
            setError("Email o contraseña incorrectos");
        } finally {
            setIsSubmitting(false);
        }
    }

    if (user) {
        return <Navigate to="/" replace />;
    }

    return (
        <div className="auth-page">
            <form className="auth-form" onSubmit={handleSubmit}>
                <h1>Iniciar sesión</h1>
                {error && <p className="auth-error">{error}</p>}
                <label>
                    Email
                    <input
                        type="email"
                        value={email}
                        onChange={(event) => setEmail(event.target.value)}
                        autoComplete="email"
                        required
                    />
                </label>
                <label>
                    Contraseña
                    <input
                        type="password"
                        value={password}
                        onChange={(event) => setPassword(event.target.value)}
                        autoComplete="current-password"
                        required
                    />
                </label>
                <button type="submit" disabled={isSubmitting}>
                    {isSubmitting ? "Entrando..." : "Entrar"}
                </button>
                <p className="auth-switch">
                    ¿No tienes cuenta? <Link to="/register">Regístrate</Link>
                </p>
            </form>
        </div>
    );
}
