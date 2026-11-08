import { useState, type FormEvent } from "react";
import { PRIORITY_LABELS, type TaskCreateInput, type TaskPriority } from "../api/tasks";
import "./TaskForm.css";

interface TaskFormProps {
    onCreate: (input: TaskCreateInput) => Promise<void>;
}

const PRIORITIES: TaskPriority[] = ["low", "medium", "high"];

export function TaskForm({ onCreate }: TaskFormProps) {
    const [title, setTitle] = useState("");
    const [description, setDescription] = useState("");
    const [priority, setPriority] = useState<TaskPriority>("medium");
    const [dueDate, setDueDate] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    async function handleSubmit(event: FormEvent) {
        event.preventDefault();
        setError(null);
        setIsSubmitting(true);
        try {
            await onCreate({
                title,
                description: description || undefined,
                priority,
                due_date: dueDate || undefined,
            });
            setTitle("");
            setDescription("");
            setPriority("medium");
            setDueDate("");
        } catch {
            setError("No se pudo crear la tarea");
        } finally {
            setIsSubmitting(false);
        }
    }

    return (
        <form className="task-form" onSubmit={handleSubmit}>
            {error && <p className="task-form-error">{error}</p>}
            <div className="task-form-row">
                <input
                    type="text"
                    placeholder="Título de la tarea"
                    value={title}
                    onChange={(event) => setTitle(event.target.value)}
                    required
                    className="task-form-title"
                />
                <select value={priority} onChange={(event) => setPriority(event.target.value as TaskPriority)}>
                    {PRIORITIES.map((value) => (
                        <option key={value} value={value}>
                            {PRIORITY_LABELS[value]}
                        </option>
                    ))}
                </select>
                <input type="date" value={dueDate} onChange={(event) => setDueDate(event.target.value)} />
                <button type="submit" disabled={isSubmitting}>
                    {isSubmitting ? "Creando..." : "Añadir"}
                </button>
            </div>
            <textarea
                placeholder="Descripción (opcional)"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                rows={2}
            />
        </form>
    );
}
