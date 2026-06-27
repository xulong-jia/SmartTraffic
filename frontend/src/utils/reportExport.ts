import type {
  ReportAnnotatedVideoSummary,
  ReportBundleResponse,
  ReportExportSection,
  ReportJsonExportResponse,
  ReportKeyframeSummary,
  ReportSummaryResponse
} from "../types";

export const REPORT_NOT_FOR_ENFORCEMENT_WARNING =
  "SmartTraffic 报告仅用于分析和复核，不作为正式交通执法依据。";

export const REPORT_EXPORT_SECTIONS: Array<{
  key: ReportExportSection;
  label: string;
  description: string;
}> = [
  { key: "events", label: "事件 Events", description: "检测到的交通事件" },
  { key: "alerts", label: "告警 Alerts", description: "告警中心记录" },
  { key: "flow_counts", label: "流量统计 Flow counts", description: "计数线记录" },
  {
    key: "zone_statistics",
    label: "区域统计 Zone statistics",
    description: "区域占用和指标窗口"
  },
  { key: "bad_cases", label: "坏例 Bad cases", description: "复核和评测坏例" },
  {
    key: "evaluation_results",
    label: "评测结果 Evaluation results",
    description: "评测指标记录"
  }
];

export function buildReportSummaryCards(summary: ReportSummaryResponse | null) {
  const counts = summary?.counts;
  return [
    { label: "事件 Events", value: counts?.events_count ?? 0 },
    { label: "告警 Alerts", value: counts?.alerts_count ?? 0 },
    { label: "流量记录 Flow records", value: counts?.flow_count_records ?? 0 },
    { label: "区域窗口 Zone windows", value: counts?.zone_statistics_records ?? 0 },
    { label: "坏例 Bad cases", value: counts?.bad_cases_count ?? 0 },
    { label: "评测结果 Evaluation results", value: counts?.evaluation_results_count ?? 0 }
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
  section: ReportExportSection | "full_report" | "report",
  extension: "csv" | "json" | "pdf"
): string {
  if (extension === "pdf" && section === "report") {
    return `smarttraffic_report_${safeName(runId)}.pdf`;
  }
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
    return "请选择一个分析任务，准备报告导出。";
  }
  const total = Object.values(summary.counts).reduce((sum, value) => sum + value, 0);
  return total > 0
    ? "报告区块已可导出。"
    : "当前任务暂无可导出的报告行。";
}

export function buildBundleSectionLabel(bundle: ReportBundleResponse | null): string {
  if (!bundle) {
    return "暂无 bundle metadata。";
  }
  return `${bundle.included_sections.length} sections: ${bundle.included_sections.join(", ")}`;
}

export function buildArtifactReferenceRows(bundle: ReportBundleResponse | null) {
  return (bundle?.artifact_references ?? []).map((item) => ({
    key: item.key,
    type: item.artifact_type,
    path: item.path || "-",
    status: item.exists ? "可用 Available" : "不可用 Unavailable",
    note: item.note
  }));
}

export function buildKeyframeSummaryRows(summary: ReportKeyframeSummary | null) {
  return (summary?.keyframe_items ?? []).map((item) => ({
    source: `${item.source_type || "unknown"}:${item.source_id || "-"}`,
    frame: item.frame_index ?? "-",
    timestamp: item.timestamp_ms ?? "-",
    path: item.path || "-",
    status: item.status
  }));
}

export function buildAnnotatedVideoLabel(summary: ReportAnnotatedVideoSummary | null): string {
  if (!summary) {
    return "标注视频 metadata 尚未加载。";
  }
  if (summary.available) {
    return `可用 Available: ${summary.annotated_video_reference || "annotated_video.mp4"}`;
  }
  return `不可用 Unavailable (${summary.status}): ${summary.notes}`;
}

function safeName(value: string): string {
  return value.replace(/[^A-Za-z0-9_-]/g, "_");
}
