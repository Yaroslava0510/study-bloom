import { apiGet, apiPost } from "./client";

export type AuthUser = {
  id: number;
  email: string;
  name: string;
};

export type RegisterInput = {
  email: string;
  password: string;
  name?: string;
};

export type LoginInput = {
  email: string;
  password: string;
};

export async function register(input: RegisterInput): Promise<AuthUser> {
  return apiPost<AuthUser>("/api/v1/auth/register", input);
}

export async function login(input: LoginInput): Promise<AuthUser> {
  return apiPost<AuthUser>("/api/v1/auth/login", input);
}

export async function logout(): Promise<void> {
  return apiPost<void>("/api/v1/auth/logout");
}

export async function getCurrentUser(): Promise<AuthUser> {
  return apiGet<AuthUser>("/api/v1/auth/me");
}

export async function requestPasswordReset(email: string): Promise<{ ok: boolean }> {
  return apiPost<{ ok: boolean }>("/api/v1/auth/password-reset/request", { email });
}

export async function verifyPasswordReset(
  email: string,
  code: string,
): Promise<{ ok: boolean; token: string }> {
  return apiPost<{ ok: boolean; token: string }>(
    "/api/v1/auth/password-reset/verify",
    { email, code },
  );
}

export async function completePasswordReset(
  email: string,
  token: string,
  password: string,
): Promise<{ ok: boolean }> {
  return apiPost<{ ok: boolean }>("/api/v1/auth/password-reset/complete", {
    email,
    token,
    password,
  });
}
