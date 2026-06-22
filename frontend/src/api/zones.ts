import { apiGet } from "./client";

export function listZones(): Promise<Record<string, string>> {
  return apiGet<Record<string, string>>("/api/zones");
}
