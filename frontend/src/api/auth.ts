import apiClient from "./client";

export interface AuthUser {
    id: string;
    email: string;
    created_at: string;
}

export interface TokenPair {
    access_token: string;
    refresh_token: string;
    token_type: string;
}

export async function loginRequest(email: string, password: string): Promise<TokenPair> {
    // POST /auth/login espera OAuth2PasswordRequestForm (form-urlencoded, campo
    // "username"), no JSON -- así funciona el botón "Authorize" de /docs en el backend.
    const body = new URLSearchParams();
    body.set("username", email);
    body.set("password", password);

    const { data } = await apiClient.post<TokenPair>("/auth/login", body, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    return data;
}

export async function registerRequest(email: string, password: string): Promise<AuthUser> {
    const { data } = await apiClient.post<AuthUser>("/auth/register", { email, password });
    return data;
}

export async function fetchCurrentUser(): Promise<AuthUser> {
    const { data } = await apiClient.get<AuthUser>("/auth/me");
    return data;
}
