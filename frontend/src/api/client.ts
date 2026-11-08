import axios from "axios";

const apiClient = axios.create({
    baseURL: import.meta.env.VITE_API_URL,
});

export default apiClient;

apiClient.interceptors.request.use((config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Si varias peticiones fallan con 401 a la vez (p. ej. la página carga y dispara
// varias llamadas en paralelo), todas deben esperar al mismo refresh en vez de
// disparar un POST /auth/refresh cada una -- este promise compartido las dedupe.
let refreshInFlight: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) {
        throw new Error("No hay refresh_token guardado");
    }

    const { data } = await axios.post(`${import.meta.env.VITE_API_URL}/auth/refresh`, {
        refresh_token: refreshToken,
    });

    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    return data.access_token;
}

apiClient.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;

        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;

            try {
                refreshInFlight ??= refreshAccessToken().finally(() => {
                    refreshInFlight = null;
                });
                const newAccessToken = await refreshInFlight;

                originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
                return apiClient(originalRequest);
            } catch {
                localStorage.removeItem("access_token");
                localStorage.removeItem("refresh_token");
                window.location.href = "/login";
            }
        }

        return Promise.reject(error);
    }
);
