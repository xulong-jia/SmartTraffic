import type {
  BadCaseModule,
  BadCaseRecord,
  BadCaseStatus,
  BadCaseType
} from "../types";

export const BAD_CASE_STATUS_KEYS = ["open", "triaged", "fixed", "verified", "wont_fix"] as const;
export const BAD_CASE_TYPE_KEYS = [
  "false_positive",
  "false_negative",
  "detection_miss",
  "detection_false_positive",
  "tracking_fragmentation",
  "id_switch",
  "trajectory_error",
  "event_rule_error",
  "annotation_error",
  "other"
] as const;
export const BAD_CASE_MODULE_KEYS = [
  "detector",
  "tracker",
  "trajectory",
  "event_engine",
  "review_center",
  "visualization",
  "other"
] as const;

export type BadCaseStatusCountKey = (typeof BAD_CASE_STATUS_KEYS)[number] | "unknown";
export type BadCaseTypeCountKey = (typeof BAD_CASE_TYPE_KEYS)[number] | "unknown";
export type BadCaseModuleCountKey = (typeof BAD_CASE_MODULE_KEYS)[number] | "unknown";
export type BadCaseStatusCounts = Record<BadCaseStatusCountKey, number>;
export type BadCaseTypeCounts = Record<BadCaseTypeCountKey, number>;
export type BadCaseModuleCounts = Record<BadCaseModuleCountKey, number>;

export interface BadCaseDisplaySummary {
  caseId: string;
  runId: string;
  caseType: string;
  module: string;
  statusLabel: string;
  event: string;
  track: string;
  frame: string;
  tags: string;
  source: string;
  linkedFailedCaseId: string;
  updatedAt: string;
}

export function buildBadCaseStatusCounts(cases: BadCaseRecord[]): BadCaseStatusCounts {
  const counts = emptyStatusCounts();
  for (const badCase of cases) {
    counts[toStatusCountKey(badCase.status)] += 1;
  }
  return counts;
}

export function buildBadCaseTypeCounts(cases: BadCaseRecord[]): BadCaseTypeCounts {
  const counts = emptyTypeCounts();
  for (const badCase of cases) {
    counts[toTypeCountKey(badCase.case_type)] += 1;
  }
  return counts;
}

export function buildBadCaseModuleCounts(cases: BadCaseRecord[]): BadCaseModuleCounts {
  const counts = emptyModuleCounts();
  for (const badCase of cases) {
    counts[toModuleCountKey(badCase.module)] += 1;
  }
  return counts;
}

export function normalizeBadCaseTags(value: string[] | string | null | undefined): string[] {
  const tags = Array.isArray(value) ? value : String(value ?? "").split(",");
  return tags.map((tag) => tag.trim()).filter(Boolean);
}

export function formatBadCaseStatusLabel(
  status: BadCaseStatus | string | null | undefined
): string {
  return formatBadCaseLabel(status);
}

export function formatBadCaseTypeLabel(
  caseType: BadCaseType | string | null | undefined
): string {
  return formatBadCaseLabel(caseType);
}

export function formatBadCaseModuleLabel(
  module: BadCaseModule | string | null | undefined
): string {
  return formatBadCaseLabel(module);
}

export function buildBadCaseDisplaySummary(
  badCase: Pick<
    BadCaseRecord,
    | "case_id"
    | "run_id"
    | "case_type"
    | "module"
    | "status"
    | "source"
    | "linked_failed_case_id"
    | "event_id"
    | "track_id"
    | "frame_index"
    | "tags"
    | "updated_at"
  >
): BadCaseDisplaySummary {
  return {
    caseId: normalizeText(badCase.case_id),
    runId: normalizeText(badCase.run_id),
    caseType: formatBadCaseTypeLabel(badCase.case_type),
    module: formatBadCaseModuleLabel(badCase.module),
    statusLabel: formatBadCaseStatusLabel(badCase.status),
    event: normalizeValue(badCase.event_id),
    track: normalizeValue(badCase.track_id),
    frame: normalizeValue(badCase.frame_index),
    tags: normalizeBadCaseTags(badCase.tags).join(", ") || "-",
    source: normalizeText(badCase.source),
    linkedFailedCaseId: normalizeValue(badCase.linked_failed_case_id),
    updatedAt: normalizeText(badCase.updated_at)
  };
}

export function normalizeBadCaseValue(value: string | number | null | undefined): string {
  return normalizeValue(value);
}

function emptyStatusCounts(): BadCaseStatusCounts {
  return { open: 0, triaged: 0, fixed: 0, verified: 0, wont_fix: 0, unknown: 0 };
}

function emptyTypeCounts(): BadCaseTypeCounts {
  return {
    false_positive: 0,
    false_negative: 0,
    detection_miss: 0,
    detection_false_positive: 0,
    tracking_fragmentation: 0,
    id_switch: 0,
    trajectory_error: 0,
    event_rule_error: 0,
    annotation_error: 0,
    other: 0,
    unknown: 0
  };
}

function emptyModuleCounts(): BadCaseModuleCounts {
  return {
    detector: 0,
    tracker: 0,
    trajectory: 0,
    event_engine: 0,
    review_center: 0,
    visualization: 0,
    other: 0,
    unknown: 0
  };
}

function toStatusCountKey(status: string | null | undefined): BadCaseStatusCountKey {
  if (BAD_CASE_STATUS_KEYS.includes(status as (typeof BAD_CASE_STATUS_KEYS)[number])) {
    return status as BadCaseStatusCountKey;
  }
  return "unknown";
}

function toTypeCountKey(caseType: string | null | undefined): BadCaseTypeCountKey {
  if (BAD_CASE_TYPE_KEYS.includes(caseType as (typeof BAD_CASE_TYPE_KEYS)[number])) {
    return caseType as BadCaseTypeCountKey;
  }
  return "unknown";
}

function toModuleCountKey(module: string | null | undefined): BadCaseModuleCountKey {
  if (BAD_CASE_MODULE_KEYS.includes(module as (typeof BAD_CASE_MODULE_KEYS)[number])) {
    return module as BadCaseModuleCountKey;
  }
  return "unknown";
}

function formatBadCaseLabel(value: string | null | undefined): string {
  return normalizeText(value, "unknown")
    .split("_")
    .filter(Boolean)
    .map((part, index) => (index === 0 ? capitalize(part) : part))
    .join(" ");
}

function normalizeValue(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return String(value);
}

function normalizeText(value: string | null | undefined, fallback = "-"): string {
  const trimmed = value?.trim();
  return trimmed ? trimmed : fallback;
}

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}
