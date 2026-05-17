"use client";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type FetchOptions = RequestInit & { auth?: boolean };

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("jrd_token");
}

export function setToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem("jrd_token", token);
  else window.localStorage.removeItem("jrd_token");
}

export async function api<T>(path: string, opts: FetchOptions = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((opts.headers as Record<string, string>) ?? {}),
  };
  const token = getToken();
  if (token && opts.auth !== false) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...opts,
    headers,
    cache: "no-store",
  });

  const contentType = res.headers.get("content-type") || "";
  const body = contentType.includes("application/json") ? await res.json() : await res.text();

  if (!res.ok) {
    const message =
      typeof body === "object" && body && "detail" in body ? String((body as { detail: unknown }).detail) : res.statusText;
    throw new ApiError(message, res.status, body);
  }
  return body as T;
}

export const apiClient = {
  get: <T>(path: string, opts?: FetchOptions) => api<T>(path, { ...opts, method: "GET" }),
  post: <T>(path: string, body: unknown, opts?: FetchOptions) =>
    api<T>(path, { ...opts, method: "POST", body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown, opts?: FetchOptions) =>
    api<T>(path, { ...opts, method: "PUT", body: JSON.stringify(body) }),
  del: <T>(path: string, opts?: FetchOptions) => api<T>(path, { ...opts, method: "DELETE" }),
};
