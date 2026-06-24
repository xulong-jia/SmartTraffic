import { apiGet, apiPost } from "./client";
import type {
  AnalysisRunListParams,
  AnalysisRunListResponse,
  AnalysisRunDetections,
  AnalysisRunSummary,
  AnalysisRunTracks,
  AlertsResponse,
  EventsResponse,
  FlowCountsArtifact,
  GenerateAlertsResponse,
  TrajectoryPointsResponse,
  ZoneStatisticsArtifact
} from "../types";

export function listAnalysisRuns(
  params: AnalysisRunListParams = {}
): Promise<AnalysisRunListResponse> {
  const queryString = buildQueryString(params);
  return apiGet<AnalysisRunSummary[] | AnalysisRunListResponse>(
    `/api/analysis-runs${queryString}`
  ).then((payload) =>
    Array.isArray(payload)
      ? { items: payload, total: payload.length, limit: payload.length, offset: 0 }
      : payload
  );
}

export function getAnalysisRun(runId: string): Promise<AnalysisRunSummary> {
  return apiGet<AnalysisRunSummary>(`/api/analysis-runs/${encodeURIComponent(runId)}`);
}

export function getAnalysisRunManifest(runId: string): Promise<Record<string, unknown>> {
  return apiGet<Record<string, unknown>>(
    `/api/analysis-runs/${encodeURIComponent(runId)}/manifest`
  );
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

export function getAnalysisRunTrajectoryPoints(
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

export const getTrajectoryPoints = getAnalysisRunTrajectoryPoints;

export function getAnalysisRunEvents(
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

export const getEvents = getAnalysisRunEvents;

export function generateAlerts(runId: string): Promise<GenerateAlertsResponse> {
  return apiPost<GenerateAlertsResponse>(
    `/api/analysis-runs/${encodeURIComponent(runId)}/alerts/generate`
  );
}

export function getAnalysisRunAlerts(
  runId: string,
  options: {
    limit?: number;
    status?: string | null;
    level?: string | null;
    eventType?: string | null;
  } = {}
): Promise<AlertsResponse> {
  const params = new URLSearchParams();
  params.set("limit", String(options.limit ?? 100));
  if (options.status) {
    params.set("status", options.status);
  }
  if (options.level) {
    params.set("level", options.level);
  }
  if (options.eventType) {
    params.set("event_type", options.eventType);
  }

  return apiGet<AlertsResponse>(
    `/api/analysis-runs/${encodeURIComponent(runId)}/alerts?${params.toString()}`
  );
}

export const getAlerts = getAnalysisRunAlerts;

export function getAnalysisRunFlowCounts(runId: string): Promise<FlowCountsArtifact> {
  return apiGet<FlowCountsArtifact>(
    `/api/analysis-runs/${encodeURIComponent(runId)}/flow-counts`
  );
}

export function getAnalysisRunZoneStatistics(runId: string): Promise<ZoneStatisticsArtifact> {
  return apiGet<ZoneStatisticsArtifact>(
    `/api/analysis-runs/${encodeURIComponent(runId)}/zone-statistics`
  );
}

function buildQueryString(params: AnalysisRunListParams): string {
  const query = new URLSearchParams();
  if (params.status) {
    query.set("status", params.status);
  }
  if (params.video_id) {
    query.set("video_id", params.video_id);
  }
  if (params.limit !== undefined) {
    query.set("limit", String(params.limit));
  }
  if (params.offset !== undefined) {
    query.set("offset", String(params.offset));
  }
  const serialized = query.toString();
  return serialized ? `?${serialized}` : "";
}
