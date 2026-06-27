import type { ReviewEventSummary, ReviewStatus } from "../types";

export const REVIEW_STATUS_KEYS = [
  "pending",
  "confirmed",
  "false_positive",
  "false_negative",
  "ignored",
  "resolved"
] as const;

export type ReviewStatusCountKey = (typeof REVIEW_STATUS_KEYS)[number] | "unknown";
export type ReviewStatusCounts = Record<ReviewStatusCountKey, number>;

export interface ReviewEventDisplaySummary {
  eventId: string;
  runId: string;
  eventType: string;
  statusLabel: string;
  originalStatus: string;
  track: string;
  zone: string;
  frameRange: string;
  linkedAlertCount: string;
  commentCount: string;
}

export function buildReviewStatusCounts(events: ReviewEventSummary[]): ReviewStatusCounts {
  const counts = emptyReviewStatusCounts();
  for (const event of events) {
    const status = toReviewStatusCountKey(event.review_status);
    counts[status] += 1;
  }
  return counts;
}

export function formatReviewStatusLabel(status: ReviewStatus | string | null | undefined): string {
  const normalized = normalizeReviewText(status, "unknown");
  const labels: Record<string, string> = {
    pending: "待复核 pending",
    confirmed: "已确认 confirmed",
    false_positive: "误报 false_positive",
    false_negative: "漏报 false_negative",
    ignored: "已忽略 ignored",
    resolved: "已解决 resolved",
    unknown: "未知 unknown"
  };
  return labels[normalized] ?? normalized;
}

export function buildReviewEventDisplaySummary(
  event: ReviewEventSummary
): ReviewEventDisplaySummary {
  return {
    eventId: normalizeReviewText(event.event_id),
    runId: normalizeReviewText(event.run_id),
    eventType: normalizeReviewText(event.event_type),
    statusLabel: formatReviewStatusLabel(event.review_status),
    originalStatus: normalizeReviewText(event.original_status),
    track: normalizeReviewValue(event.track_id),
    zone: normalizeReviewValue(event.zone_id),
    frameRange: `${normalizeReviewValue(event.start_frame)} ${normalizeReviewValue(event.end_frame)}`,
    linkedAlertCount: String(event.linked_alert_ids?.length ?? 0),
    commentCount: String(event.comment_count ?? 0)
  };
}

export function normalizeReviewValue(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return String(value);
}

function emptyReviewStatusCounts(): ReviewStatusCounts {
  return {
    pending: 0,
    confirmed: 0,
    false_positive: 0,
    false_negative: 0,
    ignored: 0,
    resolved: 0,
    unknown: 0
  };
}

function toReviewStatusCountKey(status: string | null | undefined): ReviewStatusCountKey {
  if (REVIEW_STATUS_KEYS.includes(status as (typeof REVIEW_STATUS_KEYS)[number])) {
    return status as ReviewStatusCountKey;
  }
  return "unknown";
}

function normalizeReviewText(value: string | null | undefined, fallback = "-"): string {
  const trimmed = value?.trim();
  return trimmed ? trimmed : fallback;
}
