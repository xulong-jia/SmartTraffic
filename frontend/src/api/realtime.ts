import { apiGet, apiPost } from "./client";
import type {
  RealtimeAlert,
  RealtimeEvent,
  RealtimeFrame,
  RealtimeRecentResponse,
  RealtimeStatus
} from "../types";

export function startRealtimePreview(cameraId: string): Promise<RealtimeStatus> {
  return apiPost<RealtimeStatus>(`/api/realtime/${cameraId}/start`);
}

export function stopRealtimePreview(cameraId: string): Promise<RealtimeStatus> {
  return apiPost<RealtimeStatus>(`/api/realtime/${cameraId}/stop`);
}

export function getRealtimeStatus(cameraId: string): Promise<RealtimeStatus> {
  return apiGet<RealtimeStatus>(`/api/realtime/${cameraId}/status`);
}

export function getRecentFrames(cameraId: string): Promise<RealtimeRecentResponse<RealtimeFrame>> {
  return apiGet<RealtimeRecentResponse<RealtimeFrame>>(
    `/api/realtime/${cameraId}/recent-frames`
  );
}

export function getRecentEvents(cameraId: string): Promise<RealtimeRecentResponse<RealtimeEvent>> {
  return apiGet<RealtimeRecentResponse<RealtimeEvent>>(
    `/api/realtime/${cameraId}/recent-events`
  );
}

export function getRecentAlerts(cameraId: string): Promise<RealtimeRecentResponse<RealtimeAlert>> {
  return apiGet<RealtimeRecentResponse<RealtimeAlert>>(
    `/api/realtime/${cameraId}/recent-alerts`
  );
}
