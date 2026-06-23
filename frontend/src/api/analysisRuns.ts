import { apiGet } from "./client";
import type {
  AnalysisRun,
  AnalysisRunDetections,
  AnalysisRunTracks,
  EventsResponse,
  TrajectoryPointsResponse
} from "../types";

export function listAnalysisRuns(): Promise<AnalysisRun[]> {
  return apiGet<AnalysisRun[]>("/api/analysis-runs");
}

export function getAnalysisRun(runId: string): Promise<AnalysisRun> {
  return apiGet<AnalysisRun>(`/api/analysis-runs/${encodeURIComponent(runId)}`);
}

export function getAnalysisRunDetections(
  runId: string,
  limit = 50
): Promise<AnalysisRunDetections> {
  return apiGet<AnalysisRunDetections>(
    `/api/analysis-runs/${encodeURIComponent(runId)}/detections?limit=${limit}`
  );
}

export function getAnalysisRunTracks(
  runId: string,
  limit = 50
): Promise<AnalysisRunTracks> {
  return apiGet<AnalysisRunTracks>(
    `/api/analysis-runs/${encodeURIComponent(runId)}/tracks?limit=${limit}`
  );
}

export function getTrajectoryPoints(
  runId: string,
  options: { limit?: number; trackId?: number | null } = {}
): Promise<TrajectoryPointsResponse> {
  const params = new URLSearchParams();
  params.set("limit", String(options.limit ?? 100));
  if (options.trackId !== undefined && options.trackId !== null) {
    params.set("track_id", String(options.trackId));
  }

  return apiGet<TrajectoryPointsResponse>(
    `/api/analysis-runs/${encodeURIComponent(runId)}/trajectory-points?${params.toString()}`
  );
}

export function getEvents(
  runId: string,
  options: { limit?: number; eventType?: string | null; trackId?: number | null } = {}
): Promise<EventsResponse> {
  const params = new URLSearchParams();
  params.set("limit", String(options.limit ?? 100));
  if (options.eventType) {
    params.set("event_type", options.eventType);
  }
  if (options.trackId !== undefined && options.trackId !== null) {
    params.set("track_id", String(options.trackId));
  }

  return apiGet<EventsResponse>(
    `/api/analysis-runs/${encodeURIComponent(runId)}/events?${params.toString()}`
  );
}
