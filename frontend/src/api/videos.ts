import { apiGet, apiPost } from "./client";
import type { DetectionProcessOptions, DetectionProcessResult, VideoRecord } from "../types";

export function listVideos(): Promise<VideoRecord[]> {
  return apiGet<VideoRecord[]>("/api/videos");
}

export function uploadVideo(file: File): Promise<VideoRecord> {
  const formData = new FormData();
  formData.append("file", file);
  return apiPost<VideoRecord>("/api/videos/upload", formData);
}

export function startVideoProcessing(
  videoId: string,
  options: DetectionProcessOptions = { dry_run: true }
): Promise<DetectionProcessResult> {
  return apiPost<DetectionProcessResult>(
    `/api/videos/${videoId}/process`,
    JSON.stringify(options)
  );
}
