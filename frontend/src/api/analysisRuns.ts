import { apiGet } from "./client";
import type { AnalysisRun } from "../types";

export function listAnalysisRuns(): Promise<AnalysisRun[]> {
  return apiGet<AnalysisRun[]>("/api/analysis-runs");
}
