import { useAuth } from "../context/useAuth";
import "./DashboardPage.css";

// Placeholder de F3: solo demuestra que ProtectedRoute + AuthContext funcionan.
// F4 (tareas), F5 (calendario) y F6 (chat) construyen el contenido real aquí.
export function DashboardPage() {
    const { user, logout } = useAuth();

    return (
        <div className="dashboard-page">
            <header className="dashboard-header">
                <span>Hola, {user?.email}</span>
                <button type="button" onClick={logout}>
                    Cerrar sesión
                </button>
            </header>
            <p>Próximamente: tareas, calendario y chat.</p>
        </div>
    );
}
