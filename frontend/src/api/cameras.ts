import { apiDelete, apiGet, apiPatch, apiPost } from "./client";
import type { CameraCreatePayload, CameraRecord, CameraUpdatePayload } from "../types";

export function listCameras(): Promise<CameraRecord[]> {
  return apiGet<CameraRecord[]>("/api/cameras");
}

export function createCamera(payload: CameraCreatePayload): Promise<CameraRecord> {
  return apiPost<CameraRecord>("/api/cameras", JSON.stringify(payload));
}

export function updateCamera(
  cameraId: string,
  payload: CameraUpdatePayload
): Promise<CameraRecord> {
  return apiPatch<CameraRecord>(`/api/cameras/${cameraId}`, payload);
}

export function deleteCamera(cameraId: string): Promise<{ deleted: boolean; camera_id: string }> {
  return apiDelete<{ deleted: boolean; camera_id: string }>(`/api/cameras/${cameraId}`);
}

export function enableCamera(cameraId: string): Promise<CameraRecord> {
  return apiPost<CameraRecord>(`/api/cameras/${cameraId}/enable`);
}

export function disableCamera(cameraId: string): Promise<CameraRecord> {
  return apiPost<CameraRecord>(`/api/cameras/${cameraId}/disable`);
}
