import { apiGet } from "./client";

export function listEvents(): Promise<Record<string, string>> {
  return apiGet<Record<string, string>>("/api/events");
}
