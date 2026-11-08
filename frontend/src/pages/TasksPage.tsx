import { useEffect, useState } from "react";
import { TaskForm } from "../components/TaskForm";
import { TaskItem } from "../components/TaskItem";
import {
    createTask,
    deleteTask,
    listTasks,
    PRIORITY_LABELS,
    STATUS_LABELS,
    updateTask,
    type Task,
    type TaskCreateInput,
    type TaskPriority,
    type TaskStatus,
    type TaskUpdateInput,
} from "../api/tasks";
import "./TasksPage.css";

type StatusFilter = TaskStatus | "all";
type PriorityFilter = TaskPriority | "all";

export function TasksPage() {
    const [tasks, setTasks] = useState<Task[]>([]);
    const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
    const [priorityFilter, setPriorityFilter] = useState<PriorityFilter>("all");
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let cancelled = false;

        // Nada de setState síncrono aquí (eslint-plugin-react-hooks: set-state-in-effect):
        // "empezar a cargar" también se marca dentro de una promesa, no en el cuerpo del efecto.
        Promise.resolve().then(() => {
            if (!cancelled) {
                setIsLoading(true);
                setError(null);
            }
        });

        listTasks({
            status: statusFilter === "all" ? undefined : statusFilter,
            priority: priorityFilter === "all" ? undefined : priorityFilter,
        })
            .then((data) => {
                if (!cancelled) {
                    setTasks(data);
                }
            })
            .catch(() => {
                if (!cancelled) {
                    setError("No se pudieron cargar las tareas");
                }
            })
            .finally(() => {
                if (!cancelled) {
                    setIsLoading(false);
                }
            });

        return () => {
            cancelled = true;
        };
    }, [statusFilter, priorityFilter]);

    async function handleCreate(input: TaskCreateInput) {
        const created = await createTask(input);
        // Solo se añade a la lista visible si pasa los filtros activos -- si no, el
        // usuario vería aparecer una tarea que su propio filtro debería ocultar.
        if (
            (statusFilter === "all" || created.status === statusFilter) &&
            (priorityFilter === "all" || created.priority === priorityFilter)
        ) {
            setTasks((current) => [created, ...current]);
        }
    }

    async function handleUpdate(id: string, input: TaskUpdateInput) {
        const updated = await updateTask(id, input);
        const stillMatchesFilters =
            (statusFilter === "all" || updated.status === statusFilter) &&
            (priorityFilter === "all" || updated.priority === priorityFilter);

        setTasks((current) =>
            stillMatchesFilters
                ? current.map((task) => (task.id === id ? updated : task))
                : current.filter((task) => task.id !== id)
        );
    }

    async function handleDelete(id: string) {
        await deleteTask(id);
        setTasks((current) => current.filter((task) => task.id !== id));
    }

    return (
        <div className="tasks-page">
            <TaskForm onCreate={handleCreate} />

            <div className="tasks-filters">
                <label>
                    Estado
                    <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}>
                        <option value="all">Todos</option>
                        {Object.entries(STATUS_LABELS).map(([value, label]) => (
                            <option key={value} value={value}>
                                {label}
                            </option>
                        ))}
                    </select>
                </label>
                <label>
                    Prioridad
                    <select
                        value={priorityFilter}
                        onChange={(event) => setPriorityFilter(event.target.value as PriorityFilter)}
                    >
                        <option value="all">Todas</option>
                        {Object.entries(PRIORITY_LABELS).map(([value, label]) => (
                            <option key={value} value={value}>
                                {label}
                            </option>
                        ))}
                    </select>
                </label>
            </div>

            {error && <p className="tasks-page-error">{error}</p>}

            {isLoading ? (
                <p>Cargando tareas...</p>
            ) : tasks.length === 0 ? (
                <p className="tasks-empty">No hay tareas que coincidan con el filtro.</p>
            ) : (
                <ul className="tasks-list">
                    {tasks.map((task) => (
                        <TaskItem key={task.id} task={task} onUpdate={handleUpdate} onDelete={handleDelete} />
                    ))}
                </ul>
            )}
        </div>
    );
}
