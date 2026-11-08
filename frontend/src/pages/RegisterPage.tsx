import axios from "axios";
import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../context/useAuth";
import "./AuthPages.css";

const MIN_PASSWORD_LENGTH = 8;

export function RegisterPage() {
    const { register, user } = useAuth();
    const navigate = useNavigate();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    async function handleSubmit(event: FormEvent) {
        event.preventDefault();
        setError(null);

        if (password.length < MIN_PASSWORD_LENGTH) {
            setError(`La contraseña debe tener al menos ${MIN_PASSWORD_LENGTH} caracteres`);
            return;
        }

        setIsSubmitting(true);
        try {
            await register(email, password);
            navigate("/", { replace: true });
        } catch (err) {
            if (axios.isAxiosError(err) && err.response?.status === 400) {
                setError("Ese email ya está registrado");
            } else {
                setError("No se pudo crear la cuenta");
            }
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
                <h1>Crear cuenta</h1>
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
                        autoComplete="new-password"
                        minLength={MIN_PASSWORD_LENGTH}
                        required
                    />
                </label>
                <button type="submit" disabled={isSubmitting}>
                    {isSubmitting ? "Creando cuenta..." : "Crear cuenta"}
                </button>
                <p className="auth-switch">
                    ¿Ya tienes cuenta? <Link to="/login">Inicia sesión</Link>
                </p>
            </form>
        </div>
    );
}
