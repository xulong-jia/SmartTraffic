import { apiGet, apiPost } from "./client";
import type {
  EvaluationDatasetCreateRequest,
  EvaluationDatasetListResponse,
  EvaluationDatasetRecord,
  EvaluationFailedCaseListResponse,
  EvaluationResultListResponse,
  EvaluationRunListResponse,
  EvaluationRunRequest,
  EvaluationRunResponse,
  EvaluationSummaryArtifact
} from "../types";

export function listEvaluationDatasets(): Promise<EvaluationDatasetListResponse> {
  return apiGet<EvaluationDatasetListResponse>("/api/evaluation/datasets");
}

export function registerEvaluationDataset(
  body: EvaluationDatasetCreateRequest
): Promise<EvaluationDatasetRecord> {
  return apiPost<EvaluationDatasetRecord>("/api/evaluation/datasets", JSON.stringify(body));
}

export function listEvaluationRuns(
  params: {
    run_id?: string;
    dataset_id?: string;
    evaluation_type?: string;
    limit?: number;
    offset?: number;
  } = {}
): Promise<EvaluationRunListResponse> {
  return apiGet<EvaluationRunListResponse>(`/api/evaluation/runs${buildQueryString(params)}`);
}

export function runEvaluation(body: EvaluationRunRequest): Promise<EvaluationRunResponse> {
  return apiPost<EvaluationRunResponse>("/api/evaluation/run", JSON.stringify(body));
}

export function listEvaluationResults(
  params: {
    run_id?: string;
    evaluation_run_id?: string;
    evaluation_type?: string;
    limit?: number;
    offset?: number;
  } = {}
): Promise<EvaluationResultListResponse> {
  return apiGet<EvaluationResultListResponse>(
    `/api/evaluation/results${buildQueryString(params)}`
  );
}

export function getEvaluationSummary(runId: string): Promise<EvaluationSummaryArtifact> {
  return apiGet<EvaluationSummaryArtifact>(`/api/evaluation/summary/${encodeURIComponent(runId)}`);
}

export function listEvaluationFailedCases(
  params: {
    run_id?: string;
    evaluation_run_id?: string;
    limit?: number;
    offset?: number;
  } = {}
): Promise<EvaluationFailedCaseListResponse> {
  return apiGet<EvaluationFailedCaseListResponse>(
    `/api/evaluation/failed-cases${buildQueryString(params)}`
  );
}

function buildQueryString(params: object): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, String(value));
    }
  }
  const serialized = query.toString();
  return serialized ? `?${serialized}` : "";
}
