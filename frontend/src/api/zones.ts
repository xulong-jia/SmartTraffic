import { apiDelete, apiGet, apiPatch, apiPost } from "./client";
import type { ZonePayload, ZoneRecord, ZoneUpdatePayload } from "../types";

export function listZones(
  params: { videoId?: string; enabled?: boolean } = {}
): Promise<ZoneRecord[]> {
  const query = new URLSearchParams();
  if (params.videoId) {
    query.set("video_id", params.videoId);
  }
  if (params.enabled !== undefined) {
    query.set("enabled", String(params.enabled));
  }
  const serialized = query.toString();
  return apiGet<ZoneRecord[]>(serialized ? `/api/zones?${serialized}` : "/api/zones");
}

export function createZone(payload: ZonePayload): Promise<ZoneRecord> {
  return apiPost<ZoneRecord>("/api/zones", JSON.stringify(payload));
}

export function updateZone(zoneId: string, payload: ZoneUpdatePayload): Promise<ZoneRecord> {
  return apiPatch<ZoneRecord>(`/api/zones/${encodeURIComponent(zoneId)}`, payload);
}

export function deleteZone(zoneId: string): Promise<{ id: string; deleted: boolean }> {
  return apiDelete<{ id: string; deleted: boolean }>(`/api/zones/${encodeURIComponent(zoneId)}`);
}
