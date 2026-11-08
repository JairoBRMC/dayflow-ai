import apiClient from "./client";

export type TaskStatus = "pending" | "in_progress" | "done";
export type TaskPriority = "low" | "medium" | "high";

export interface Task {
    id: string;
    title: string;
    description: string | null;
    status: TaskStatus;
    priority: TaskPriority;
    due_date: string | null;
}

export interface TaskFilters {
    status?: TaskStatus;
    priority?: TaskPriority;
}

export interface TaskCreateInput {
    title: string;
    description?: string | null;
    priority?: TaskPriority;
    due_date?: string | null;
}

export interface TaskUpdateInput {
    title?: string;
    description?: string | null;
    status?: TaskStatus;
    priority?: TaskPriority;
    due_date?: string | null;
}

export const STATUS_LABELS: Record<TaskStatus, string> = {
    pending: "Pendiente",
    in_progress: "En progreso",
    done: "Hecha",
};

export const PRIORITY_LABELS: Record<TaskPriority, string> = {
    low: "Baja",
    medium: "Media",
    high: "Alta",
};

export async function listTasks(filters: TaskFilters = {}): Promise<Task[]> {
    const { data } = await apiClient.get<Task[]>("/tasks", { params: filters });
    return data;
}

export async function createTask(input: TaskCreateInput): Promise<Task> {
    const { data } = await apiClient.post<Task>("/tasks", input);
    return data;
}

export async function updateTask(id: string, input: TaskUpdateInput): Promise<Task> {
    const { data } = await apiClient.put<Task>(`/tasks/${id}`, input);
    return data;
}

export async function deleteTask(id: string): Promise<void> {
    await apiClient.delete(`/tasks/${id}`);
}
