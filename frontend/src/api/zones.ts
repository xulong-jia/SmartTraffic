import { apiGet } from "./client";
import type { ZoneRecord } from "../types";

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
