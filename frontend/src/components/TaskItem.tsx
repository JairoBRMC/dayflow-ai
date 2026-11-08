import { useState } from "react";
import {
    PRIORITY_LABELS,
    STATUS_LABELS,
    type Task,
    type TaskPriority,
    type TaskStatus,
    type TaskUpdateInput,
} from "../api/tasks";
import "./TaskItem.css";

interface TaskItemProps {
    task: Task;
    onUpdate: (id: string, input: TaskUpdateInput) => Promise<void>;
    onDelete: (id: string) => Promise<void>;
}

const STATUSES: TaskStatus[] = ["pending", "in_progress", "done"];
const PRIORITIES: TaskPriority[] = ["low", "medium", "high"];

export function TaskItem({ task, onUpdate, onDelete }: TaskItemProps) {
    const [isEditing, setIsEditing] = useState(false);
    const [title, setTitle] = useState(task.title);
    const [description, setDescription] = useState(task.description ?? "");
    const [status, setStatus] = useState<TaskStatus>(task.status);
    const [priority, setPriority] = useState<TaskPriority>(task.priority);
    const [dueDate, setDueDate] = useState(task.due_date ?? "");
    const [isSaving, setIsSaving] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    function startEditing() {
        setTitle(task.title);
        setDescription(task.description ?? "");
        setStatus(task.status);
        setPriority(task.priority);
        setDueDate(task.due_date ?? "");
        setError(null);
        setIsEditing(true);
    }

    async function handleSave() {
        setError(null);
        setIsSaving(true);
        try {
            await onUpdate(task.id, {
                title,
                description: description || null,
                status,
                priority,
                due_date: dueDate || null,
            });
            setIsEditing(false);
        } catch {
            setError("No se pudo guardar la tarea");
        } finally {
            setIsSaving(false);
        }
    }

    async function handleDelete() {
        if (!window.confirm(`¿Borrar "${task.title}"?`)) {
            return;
        }
        setIsDeleting(true);
        try {
            await onDelete(task.id);
        } catch {
            setError("No se pudo borrar la tarea");
            setIsDeleting(false);
        }
    }

    if (isEditing) {
        return (
            <li className="task-item task-item-editing">
                {error && <p className="task-item-error">{error}</p>}
                <input
                    type="text"
                    value={title}
                    onChange={(event) => setTitle(event.target.value)}
                    className="task-item-title-input"
                />
                <textarea
                    value={description}
                    onChange={(event) => setDescription(event.target.value)}
                    placeholder="Descripción (opcional)"
                    rows={2}
                />
                <div className="task-item-row">
                    <select value={status} onChange={(event) => setStatus(event.target.value as TaskStatus)}>
                        {STATUSES.map((value) => (
                            <option key={value} value={value}>
                                {STATUS_LABELS[value]}
                            </option>
                        ))}
                    </select>
                    <select value={priority} onChange={(event) => setPriority(event.target.value as TaskPriority)}>
                        {PRIORITIES.map((value) => (
                            <option key={value} value={value}>
                                {PRIORITY_LABELS[value]}
                            </option>
                        ))}
                    </select>
                    <input type="date" value={dueDate} onChange={(event) => setDueDate(event.target.value)} />
                </div>
                <div className="task-item-actions">
                    <button type="button" onClick={handleSave} disabled={isSaving}>
                        {isSaving ? "Guardando..." : "Guardar"}
                    </button>
                    <button type="button" onClick={() => setIsEditing(false)} disabled={isSaving}>
                        Cancelar
                    </button>
                </div>
            </li>
        );
    }

    return (
        <li className="task-item">
            {error && <p className="task-item-error">{error}</p>}
            <div className="task-item-main">
                <span className="task-item-title">{task.title}</span>
                <span className={`task-badge task-badge-status-${task.status}`}>{STATUS_LABELS[task.status]}</span>
                <span className={`task-badge task-badge-priority-${task.priority}`}>
                    {PRIORITY_LABELS[task.priority]}
                </span>
                {task.due_date && <span className="task-item-due">Vence: {task.due_date}</span>}
            </div>
            {task.description && <p className="task-item-description">{task.description}</p>}
            <div className="task-item-actions">
                <button type="button" onClick={startEditing}>
                    Editar
                </button>
                <button type="button" onClick={handleDelete} disabled={isDeleting}>
                    {isDeleting ? "Borrando..." : "Borrar"}
                </button>
            </div>
        </li>
    );
}
