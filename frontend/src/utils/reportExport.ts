import type {
  ReportExportSection,
  ReportJsonExportResponse,
  ReportSummaryResponse
} from "../types";

export const REPORT_NOT_FOR_ENFORCEMENT_WARNING =
  "SmartTraffic reports are for analysis and review only; not for traffic enforcement.";

export const REPORT_EXPORT_SECTIONS: Array<{
  key: ReportExportSection;
  label: string;
  description: string;
}> = [
  { key: "events", label: "Events", description: "Detected traffic events" },
  { key: "alerts", label: "Alerts", description: "Alert Center records" },
  { key: "flow_counts", label: "Flow counts", description: "Counting-line records" },
  {
    key: "zone_statistics",
    label: "Zone statistics",
    description: "Zone-level occupancy and metric windows"
  },
  { key: "bad_cases", label: "Bad cases", description: "Review and evaluation cases" },
  {
    key: "evaluation_results",
    label: "Evaluation results",
    description: "Evaluation metric records"
  }
];

export function buildReportSummaryCards(summary: ReportSummaryResponse | null) {
  const counts = summary?.counts;
  return [
    { label: "Events", value: counts?.events_count ?? 0 },
    { label: "Alerts", value: counts?.alerts_count ?? 0 },
    { label: "Flow records", value: counts?.flow_count_records ?? 0 },
    { label: "Zone windows", value: counts?.zone_statistics_records ?? 0 },
    { label: "Bad cases", value: counts?.bad_cases_count ?? 0 },
    { label: "Evaluation results", value: counts?.evaluation_results_count ?? 0 }
  ];
}

export function buildExportSectionOptions(
  availableExports: ReportExportSection[] | undefined
) {
  const available = new Set(availableExports ?? REPORT_EXPORT_SECTIONS.map((item) => item.key));
  return REPORT_EXPORT_SECTIONS.map((item) => ({
    ...item,
    available: available.has(item.key)
  }));
}

export function buildJsonExportPreview(payload: ReportJsonExportResponse | null): string {
  if (!payload) {
    return "";
  }
  return JSON.stringify(payload, null, 2);
}

export function buildJsonExportMetadata(payload: ReportJsonExportResponse | null) {
  if (!payload) {
    return [];
  }
  return [
    { label: "Schema", value: payload.metadata.schema_version },
    { label: "Generated", value: payload.metadata.generated_at },
    { label: "Run", value: payload.run.run_id || payload.run.id },
    { label: "Sections", value: payload.metadata.available_exports.join(", ") }
  ];
}

export function buildReportFilename(
  runId: string,
  section: ReportExportSection | "full_report",
  extension: "csv" | "json"
): string {
  return `smarttraffic_${safeName(runId)}_${safeName(section)}.${extension}`;
}

export function resolveDownloadFilename(
  contentDisposition: string | null,
  fallback: string
): string {
  const match = contentDisposition?.match(/filename="?([^";]+)"?/i);
  return match?.[1] || fallback;
}

export function buildEmptyReportState(summary: ReportSummaryResponse | null): string {
  if (!summary) {
    return "Select an analysis run to prepare report exports.";
  }
  const total = Object.values(summary.counts).reduce((sum, value) => sum + value, 0);
  return total > 0
    ? "Report sections are ready for export."
    : "This run has no reportable rows yet.";
}

function safeName(value: string): string {
  return value.replace(/[^A-Za-z0-9_-]/g, "_");
}
