import { useAuth } from "../context/useAuth";
import { TasksPage } from "./TasksPage";
import "./DashboardPage.css";

// Shell autenticado: cabecera con el usuario y logout, más el contenido de la fase
// actual. El calendario y el chat añadirán su propia navegación cuando existan.
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
            <TasksPage />
        </div>
    );
}
