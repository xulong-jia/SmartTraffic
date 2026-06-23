import { apiGet, apiPatch } from "./client";
import type { AlertCenterResponse, AlertRecord } from "../types";

export function listAlerts(
  options: {
    runId?: string | null;
    status?: string | null;
    level?: string | null;
  } = {}
): Promise<AlertCenterResponse> {
  const params = new URLSearchParams();
  if (options.runId) {
    params.set("run_id", options.runId);
  }
  if (options.status) {
    params.set("status", options.status);
  }
  if (options.level) {
    params.set("level", options.level);
  }
  const query = params.toString();
  return apiGet<AlertCenterResponse>(query ? `/api/alerts?${query}` : "/api/alerts");
}

export function getAlert(alertId: string): Promise<AlertRecord> {
  return apiGet<AlertRecord>(`/api/alerts/${encodeURIComponent(alertId)}`);
}

export function acknowledgeAlert(
  alertId: string,
  acknowledgedBy?: string
): Promise<AlertRecord> {
  return apiPatch<AlertRecord>(
    `/api/alerts/${encodeURIComponent(alertId)}/acknowledge`,
    acknowledgedBy ? { acknowledged_by: acknowledgedBy } : {}
  );
}

export function resolveAlert(alertId: string): Promise<AlertRecord> {
  return apiPatch<AlertRecord>(`/api/alerts/${encodeURIComponent(alertId)}/resolve`);
}

export function ignoreAlert(alertId: string): Promise<AlertRecord> {
  return apiPatch<AlertRecord>(`/api/alerts/${encodeURIComponent(alertId)}/ignore`);
}
