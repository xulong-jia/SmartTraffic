import { apiGet } from "./client";
import type { AnalysisRun, AnalysisRunDetections } from "../types";

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
