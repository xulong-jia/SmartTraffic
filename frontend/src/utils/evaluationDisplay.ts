import type {
  BadCaseFromFailedCaseRequest,
  EvaluationFailedCaseRecord,
  EvaluationResultRecord,
  EvaluationSummaryArtifact
} from "../types";
import {
  buildBadCaseRegressionDisplaySummary,
  buildEvaluationResultDisplaySummary,
  formatEvaluationMetricLabel,
  formatEvaluationStatusLabel,
  formatEvaluationTypeLabel,
  normalizeMetricValue
} from "./evaluationMetrics";

export interface EvaluationBoundaryNotice {
  key: string;
  label: string;
  detail: string;
}

export interface EvaluationMetricCard {
  key: string;
  label: string;
  value: string;
  status: string;
  detail: string;
}

export interface EvaluationFailedCaseRow {
  failedCaseId: string;
  evaluationRunId: string;
  runId: string;
  datasetId: string;
  failureType: string;
  module: string;
  frameRange: string;
  suggestedBadCaseType: string;
  expected: string;
  actual: string;
  createdAt: string;
}

export const EVALUATION_BOUNDARY_NOTICES: EvaluationBoundaryNotice[] = [
  {
    key: "detection-map",
    label: "Detection mAP",
    detail: "VOC-style single-IoU AP/mAP, not COCO official mAP."
  },
  {
    key: "tracking-metrics",
    label: "Tracking IDF1 / MOTA",
    detail: "Lightweight deterministic frame-level association, not TrackEval official metrics."
  },
  {
    key: "regression-rerun",
    label: "Regression replay",
    detail: "Deterministic replay / stored rule replay, not a complete video rerun."
  },
  {
    key: "insufficient-data",
    label: "Insufficient data",
    detail: "Missing annotations or replay data; it is not a zero score or failed case by itself."
  }
];

export function buildEvaluationMetricCards(
  results: EvaluationResultRecord[]
): EvaluationMetricCard[] {
  return results.map((result) => {
    const summary = buildEvaluationResultDisplaySummary(result);
    return {
      key: result.evaluation_result_id,
      label: `${summary.evaluationType} · ${summary.metricName}`,
      value: summary.metricValue,
      status: summary.statusLabel,
      detail: summary.reason
    };
  });
}

export function buildEvaluationResultJson(result: EvaluationResultRecord): string {
  return JSON.stringify(
    {
      evaluation_result_id: result.evaluation_result_id,
      evaluation_run_id: result.evaluation_run_id,
      run_id: result.run_id,
      dataset_id: result.dataset_id,
      evaluation_type: result.evaluation_type,
      metric_name: result.metric_name,
      metric_value: result.metric_value,
      details: result.details,
      created_at: result.created_at
    },
    null,
    2
  );
}

export function buildFailedCaseRows(
  failedCases: EvaluationFailedCaseRecord[]
): EvaluationFailedCaseRow[] {
  return failedCases.map((failedCase) => ({
    failedCaseId: failedCase.failed_case_id,
    evaluationRunId: failedCase.evaluation_run_id,
    runId: failedCase.run_id,
    datasetId: normalizeText(failedCase.dataset_id),
    failureType: formatEvaluationMetricLabel(failedCase.failure_type),
    module: normalizeText(failedCase.module),
    frameRange: formatFrameRange(failedCase.frame_range),
    suggestedBadCaseType: normalizeText(failedCase.suggested_bad_case_type),
    expected: stringifyCompact(failedCase.expected),
    actual: stringifyCompact(failedCase.actual),
    createdAt: normalizeText(failedCase.created_at)
  }));
}

export function buildFailedCaseBadCaseRequest(
  failedCase: EvaluationFailedCaseRecord
): BadCaseFromFailedCaseRequest {
  return {
    run_id: failedCase.run_id,
    failed_case_id: failedCase.failed_case_id,
    case_type: failedCase.suggested_bad_case_type || failedCase.failure_type || "other",
    module: failedCase.module || null,
    description: `${failedCase.failure_type} from evaluation ${failedCase.evaluation_run_id}`,
    expected_result: stringifyCompact(failedCase.expected),
    actual_result: stringifyCompact(failedCase.actual),
    root_cause: "Pending triage from Evaluation Center.",
    tags: ["evaluation", "failed_case"]
  };
}

export function buildRegressionSummaryCards(
  summary: EvaluationSummaryArtifact | null
): EvaluationMetricCard[] {
  const regression = readRecord(summary?.summary, "bad_case_regression");
  const display = buildBadCaseRegressionDisplaySummary(regression);
  return [
    {
      key: "regression-total",
      label: "Regression total",
      value: display.totalCases,
      status: display.statusLabel,
      detail: "Stored Bad Case replay scope."
    },
    {
      key: "regression-pass-rate",
      label: "Regression pass rate",
      value: display.regressionPassRate,
      status: display.statusLabel,
      detail: display.definition
    },
    {
      key: "regression-fixed",
      label: "Fixed / verified",
      value: `${display.fixedCases} / ${display.verifiedCases}`,
      status: display.statusLabel,
      detail: `Open ${display.openCases}; reopened ${display.reopenedCaseCount}.`
    }
  ];
}

export function formatEvaluationBoundaryForType(evaluationType: string): string {
  if (evaluationType === "detection") {
    return EVALUATION_BOUNDARY_NOTICES[0].detail;
  }
  if (evaluationType === "tracking") {
    return EVALUATION_BOUNDARY_NOTICES[1].detail;
  }
  if (evaluationType === "regression") {
    return EVALUATION_BOUNDARY_NOTICES[2].detail;
  }
  return `${formatEvaluationTypeLabel(evaluationType)} metrics follow the local MVP artifact contract.`;
}

export function isInsufficientDataResult(result: EvaluationResultRecord): boolean {
  return (
    result.details?.status === "insufficient_data" ||
    result.details?.reason === "not_enough_annotations"
  );
}

export function buildInsufficientDataLabel(result: EvaluationResultRecord): string {
  if (!isInsufficientDataResult(result)) {
    return formatEvaluationStatusLabel(String(result.details?.status ?? "available"));
  }
  return "Insufficient data: missing annotations/data, not a zero score.";
}

function formatFrameRange(frameRange: Record<string, number | null | undefined>): string {
  const start = frameRange.start_frame ?? frameRange.start ?? null;
  const end = frameRange.end_frame ?? frameRange.end ?? null;
  if (start === null && end === null) {
    return "-";
  }
  return `${normalizeMetricValue(start)} ${normalizeMetricValue(end)}`;
}

function stringifyCompact(value: Record<string, unknown>): string {
  const serialized = JSON.stringify(value);
  return serialized === "{}" ? "-" : serialized;
}

function readRecord(
  payload: Record<string, unknown> | null | undefined,
  key: string
): Record<string, unknown> | null {
  const value = payload?.[key];
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function normalizeText(value: string | null | undefined, fallback = "-"): string {
  const trimmed = value?.trim();
  return trimmed ? trimmed : fallback;
}
