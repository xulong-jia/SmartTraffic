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
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method: "POST",
    body
  });
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}
