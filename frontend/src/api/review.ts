import { apiGet, apiPost } from "./client";
import type {
  FalseNegativeRecord,
  FalseNegativeRequest,
  FalseNegativeResponse,
  ReviewActionRequest,
  ReviewActionResponse,
  ReviewCommentRequest,
  ReviewCommentsResponse,
  ReviewEventDetail,
  ReviewEventListResponse
} from "../types";

export interface ReviewEventListParams {
  run_id?: string;
  status?: string;
  event_type?: string;
  limit?: number;
  offset?: number;
}

export function listReviewEvents(
  params: ReviewEventListParams = {}
): Promise<ReviewEventListResponse> {
  return apiGet<ReviewEventListResponse>(`/api/review/events${buildQueryString(params)}`);
}

export function getReviewEvent(
  eventId: string,
  params: { run_id: string }
): Promise<ReviewEventDetail> {
  return apiGet<ReviewEventDetail>(
    `/api/review/events/${encodeURIComponent(eventId)}${buildQueryString(params)}`
  );
}

export function confirmReviewEvent(
  eventId: string,
  body: ReviewActionRequest
): Promise<ReviewActionResponse> {
  return postReviewJson<ReviewActionResponse>(
    `/api/review/events/${encodeURIComponent(eventId)}/confirm`,
    body
  );
}

export function markReviewEventFalsePositive(
  eventId: string,
  body: ReviewActionRequest
): Promise<ReviewActionResponse> {
  return postReviewJson<ReviewActionResponse>(
    `/api/review/events/${encodeURIComponent(eventId)}/false-positive`,
    body
  );
}

export function ignoreReviewEvent(
  eventId: string,
  body: ReviewActionRequest
): Promise<ReviewActionResponse> {
  return postReviewJson<ReviewActionResponse>(
    `/api/review/events/${encodeURIComponent(eventId)}/ignore`,
    body
  );
}

export function resolveReviewEvent(
  eventId: string,
  body: ReviewActionRequest
): Promise<ReviewActionResponse> {
  return postReviewJson<ReviewActionResponse>(
    `/api/review/events/${encodeURIComponent(eventId)}/resolve`,
    body
  );
}

export function requestReviewRuleRerun(
  eventId: string,
  body: ReviewActionRequest
): Promise<Record<string, unknown>> {
  return postReviewJson<Record<string, unknown>>(
    `/api/review/events/${encodeURIComponent(eventId)}/rerun-rule`,
    body
  );
}

export function addReviewComment(
  body: ReviewCommentRequest
): Promise<ReviewActionResponse> {
  return postReviewJson<ReviewActionResponse>("/api/review/comments", body);
}

export function listReviewComments(params: {
  run_id: string;
  event_id?: string;
  limit?: number;
  offset?: number;
}): Promise<ReviewCommentsResponse> {
  return apiGet<ReviewCommentsResponse>(`/api/review/comments${buildQueryString(params)}`);
}

export function addFalseNegative(
  body: FalseNegativeRequest
): Promise<FalseNegativeResponse> {
  return postReviewJson<FalseNegativeResponse>("/api/review/false-negatives", body);
}

function postReviewJson<T>(path: string, body: unknown): Promise<T> {
  return apiPost<T>(path, JSON.stringify(body));
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

export type { FalseNegativeRecord };
