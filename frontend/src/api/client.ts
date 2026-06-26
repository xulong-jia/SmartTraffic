const defaultBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export function getApiBaseUrl(): string {
  return defaultBaseUrl;
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function apiPost<T>(path: string, body?: BodyInit): Promise<T> {
  const init: RequestInit = {
    method: "POST",
    body
  };
  if (body && !(body instanceof FormData)) {
    init.headers = { "Content-Type": "application/json" };
  }
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init
  });
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function apiPatch<T>(path: string, body?: unknown): Promise<T> {
  const init: RequestInit = {
    method: "PATCH"
  };
  if (body !== undefined) {
    init.headers = { "Content-Type": "application/json" };
    init.body = JSON.stringify(body);
  }
  const response = await fetch(`${getApiBaseUrl()}${path}`, init);
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function apiDelete<T>(path: string): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method: "DELETE"
  });
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}
