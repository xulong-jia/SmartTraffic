import { apiGet } from "./client";

export function listAlerts(): Promise<Record<string, string>> {
  return apiGet<Record<string, string>>("/api/alerts");
}
