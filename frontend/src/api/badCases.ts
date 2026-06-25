import { apiGet, apiPatch, apiPost } from "./client";
import type {
  BadCaseCreateRequest,
  BadCaseFromReviewRequest,
  BadCaseListParams,
  BadCaseListResponse,
  BadCaseRecord,
  BadCaseSummary,
  BadCaseUpdateRequest
} from "../types";

export function listBadCases(
  params: BadCaseListParams = {}
): Promise<BadCaseListResponse> {
  return apiGet<BadCaseListResponse>(`/api/bad-cases${buildQueryString(params)}`);
}

export function getBadCase(
  caseId: string,
  params: { run_id?: string } = {}
): Promise<BadCaseRecord> {
  return apiGet<BadCaseRecord>(
    `/api/bad-cases/${encodeURIComponent(caseId)}${buildQueryString(params)}`
  );
}

export function createBadCase(body: BadCaseCreateRequest): Promise<BadCaseRecord> {
  return apiPost<BadCaseRecord>("/api/bad-cases", JSON.stringify(body));
}

export function updateBadCase(
  caseId: string,
  body: BadCaseUpdateRequest
): Promise<BadCaseRecord> {
  return apiPatch<BadCaseRecord>(`/api/bad-cases/${encodeURIComponent(caseId)}`, body);
}

export function getBadCaseSummary(
  params: { run_id?: string } = {}
): Promise<BadCaseSummary> {
  return apiGet<BadCaseSummary>(`/api/bad-cases/summary${buildQueryString(params)}`);
}

export function createBadCaseFromReview(
  body: BadCaseFromReviewRequest
): Promise<BadCaseRecord> {
  return apiPost<BadCaseRecord>("/api/bad-cases/from-review", JSON.stringify(body));
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
