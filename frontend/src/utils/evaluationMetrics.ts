import type { EvaluationResultRecord, EvaluationType } from "../types";

export const EVALUATION_STATUS_KEYS = [
  "available",
  "empty",
  "not_applicable",
  "planned"
] as const;
export const EVALUATION_TYPE_KEYS = [
  "event",
  "flow_counting",
  "trajectory",
  "detection",
  "tracking",
  "regression"
] as const;

export type EvaluationStatusCountKey =
  | (typeof EVALUATION_STATUS_KEYS)[number]
  | "unknown";
export type EvaluationStatusCounts = Record<EvaluationStatusCountKey, number>;

export interface EvaluationResultDisplaySummary {
  evaluationRunId: string;
  runId: string;
  datasetId: string;
  evaluationType: string;
  metricName: string;
  metricValue: string;
  statusLabel: string;
  reason: string;
  createdAt: string;
}

export function buildEvaluationStatusCounts(
  results: EvaluationResultRecord[]
): EvaluationStatusCounts {
  const counts = emptyStatusCounts();
  for (const result of results) {
    counts[toStatusCountKey(extractMetricStatus(result))] += 1;
  }
  return counts;
}

export function extractMetricStatus(
  result: Pick<EvaluationResultRecord, "details">
): string {
  const status = result.details?.status;
  return typeof status === "string" && status.trim() ? status : "unknown";
}

export function formatEvaluationStatusLabel(
  status: string | null | undefined
): string {
  return formatEvaluationLabel(status);
}

export function formatEvaluationTypeLabel(
  evaluationType: EvaluationType | string | null | undefined
): string {
  return formatEvaluationLabel(evaluationType);
}

export function formatEvaluationMetricLabel(
  metricName: string | null | undefined
): string {
  return formatEvaluationLabel(metricName);
}

export function normalizeMetricValue(
  value: number | string | null | undefined
): string {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(3);
  }
  return String(value);
}

export function buildEvaluationResultDisplaySummary(
  result: EvaluationResultRecord
): EvaluationResultDisplaySummary {
  return {
    evaluationRunId: normalizeText(result.evaluation_run_id),
    runId: normalizeText(result.run_id),
    datasetId: normalizeText(result.dataset_id),
    evaluationType: formatEvaluationTypeLabel(result.evaluation_type),
    metricName: formatEvaluationMetricLabel(result.metric_name),
    metricValue: normalizeMetricValue(result.metric_value),
    statusLabel: formatEvaluationStatusLabel(extractMetricStatus(result)),
    reason: normalizeText(readDetailString(result.details, "reason")),
    createdAt: normalizeText(result.created_at)
  };
}

function emptyStatusCounts(): EvaluationStatusCounts {
  return {
    available: 0,
    empty: 0,
    not_applicable: 0,
    planned: 0,
    unknown: 0
  };
}

function toStatusCountKey(status: string | null | undefined): EvaluationStatusCountKey {
  if (
    EVALUATION_STATUS_KEYS.includes(
      status as (typeof EVALUATION_STATUS_KEYS)[number]
    )
  ) {
    return status as EvaluationStatusCountKey;
  }
  return "unknown";
}

function formatEvaluationLabel(value: string | null | undefined): string {
  return normalizeText(value, "unknown")
    .split("_")
    .filter(Boolean)
    .map((part, index) => (index === 0 ? capitalize(part) : part))
    .join(" ");
}

function readDetailString(
  details: Record<string, unknown> | null | undefined,
  key: string
): string | null {
  const value = details?.[key];
  return typeof value === "string" ? value : null;
}

function normalizeText(value: string | null | undefined, fallback = "-"): string {
  const trimmed = value?.trim();
  return trimmed ? trimmed : fallback;
}

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}
