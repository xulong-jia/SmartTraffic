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
    detail: "本地 VOC-style 单 IoU AP/mAP，不是 COCO official mAP。"
  },
  {
    key: "tracking-metrics",
    label: "Tracking IDF1 / MOTA",
    detail: "轻量确定性帧级关联指标，不是 TrackEval official metrics。"
  },
  {
    key: "regression-rerun",
    label: "回归重放",
    detail: "使用确定性重放或已存规则重放，不是完整视频重跑。"
  },
  {
    key: "insufficient-data",
    label: "数据不足",
    detail: "缺少标注或重放数据时不会直接计为 0 分或失败用例。"
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
      label: "回归总数",
      value: display.totalCases,
      status: display.statusLabel,
      detail: "已存坏例重放范围。"
    },
    {
      key: "regression-pass-rate",
      label: "回归通过率",
      value: display.regressionPassRate,
      status: display.statusLabel,
      detail: display.definition
    },
    {
      key: "regression-fixed",
      label: "已修复 / 已验证",
      value: `${display.fixedCases} / ${display.verifiedCases}`,
      status: display.statusLabel,
      detail: `未处理 ${display.openCases}；重开 ${display.reopenedCaseCount}。`
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
  return `${formatEvaluationTypeLabel(evaluationType)}指标遵循本地 MVP 产物契约。`;
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
  return "数据不足：缺少标注或数据，不计为 0 分。";
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
