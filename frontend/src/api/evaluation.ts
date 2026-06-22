import { apiGet } from "./client";

export function listEvaluationResults(): Promise<Record<string, string>> {
  return apiGet<Record<string, string>>("/api/evaluation/results");
}
