import type {
  BadCaseRegressionSummary,
  EvaluationResultRecord,
  EvaluationType
} from "../types";

export const EVALUATION_STATUS_KEYS = [
  "available",
  "empty",
  "insufficient_data",
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

export interface BadCaseRegressionDisplaySummary {
  statusLabel: string;
  totalCases: string;
  openCases: string;
  fixedCases: string;
  verifiedCases: string;
  ignoredCases: string;
  fixedCaseCount: string;
  reopenedCaseCount: string;
  regressionPassRate: string;
  definition: string;
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
  const normalized = normalizeText(status, "unknown");
  const labels: Record<string, string> = {
    available: "可用",
    empty: "为空",
    insufficient_data: "数据不足",
    not_applicable: "不适用",
    planned: "计划中",
    unknown: "未知"
  };
  return labels[normalized] ?? normalized;
}

export function formatEvaluationTypeLabel(
  evaluationType: EvaluationType | string | null | undefined
): string {
  const normalized = normalizeText(evaluationType, "unknown");
  const labels: Record<string, string> = {
    event: "事件",
    flow_counting: "流量统计",
    trajectory: "轨迹",
    detection: "检测",
    tracking: "跟踪",
    regression: "回归",
    unknown: "未知"
  };
  return labels[normalized] ?? normalized;
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

export function buildBadCaseRegressionDisplaySummary(
  summary: BadCaseRegressionSummary | Record<string, unknown> | null | undefined
): BadCaseRegressionDisplaySummary {
  const payload: Record<string, unknown> =
    summary && typeof summary === "object" ? { ...summary } : {};
  return {
    statusLabel: formatEvaluationStatusLabel(readUnknownString(payload, "status")),
    totalCases: normalizeMetricValue(readUnknownNumber(payload, "total_cases")),
    openCases: normalizeMetricValue(readUnknownNumber(payload, "open_cases")),
    fixedCases: normalizeMetricValue(readUnknownNumber(payload, "fixed_cases")),
    verifiedCases: normalizeMetricValue(readUnknownNumber(payload, "verified_cases")),
    ignoredCases: normalizeMetricValue(readUnknownNumber(payload, "ignored_cases")),
    fixedCaseCount: normalizeMetricValue(readUnknownNumber(payload, "fixed_case_count")),
    reopenedCaseCount: normalizeMetricValue(readUnknownNumber(payload, "reopened_case_count")),
    regressionPassRate: normalizeMetricValue(readUnknownNumber(payload, "regression_pass_rate")),
    definition: normalizeText(readUnknownString(payload, "definition"))
  };
}

function emptyStatusCounts(): EvaluationStatusCounts {
  return {
    available: 0,
    empty: 0,
    insufficient_data: 0,
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

function readUnknownString(
  details: Record<string, unknown>,
  key: string
): string | null {
  const value = details[key];
  return typeof value === "string" ? value : null;
}

function readUnknownNumber(
  details: Record<string, unknown>,
  key: string
): number | null {
  const value = details[key];
  return typeof value === "number" ? value : null;
}

function normalizeText(value: string | null | undefined, fallback = "-"): string {
  const trimmed = value?.trim();
  return trimmed ? trimmed : fallback;
}

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}
