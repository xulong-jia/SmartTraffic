import { apiGet, getApiBaseUrl } from "./client";
import type {
  AnalysisRunListParams,
  AnalysisRunListResponse,
  AnalysisRunSummary,
  ReportBundleResponse,
  ReportExportSection,
  ReportJsonExportResponse,
  ReportSummaryResponse
} from "../types";
import { resolveDownloadFilename, buildReportFilename } from "../utils/reportExport";

export function listReportRuns(
  params: AnalysisRunListParams = {}
): Promise<AnalysisRunListResponse> {
  const queryString = buildQueryString(params);
  return apiGet<AnalysisRunSummary[] | AnalysisRunListResponse>(
    `/api/reports/runs${queryString}`
  ).then((payload) =>
    Array.isArray(payload)
      ? { items: payload, total: payload.length, limit: payload.length, offset: 0 }
      : payload
  );
}

export function getReportSummary(runId: string): Promise<ReportSummaryResponse> {
  return apiGet<ReportSummaryResponse>(
    `/api/reports/${encodeURIComponent(runId)}/summary`
  );
}

export function getReportJson(runId: string): Promise<ReportJsonExportResponse> {
  return apiGet<ReportJsonExportResponse>(
    `/api/reports/${encodeURIComponent(runId)}/export.json`
  );
}

export function getReportBundle(runId: string): Promise<ReportBundleResponse> {
  return apiGet<ReportBundleResponse>(
    `/api/reports/${encodeURIComponent(runId)}/bundle`
  );
}

export async function getReportCsv(
  runId: string,
  section: ReportExportSection
): Promise<{ blob: Blob; filename: string }> {
  const response = await fetch(
    `${getApiBaseUrl()}/api/reports/${encodeURIComponent(runId)}/export.csv?section=${encodeURIComponent(section)}`
  );
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  const fallback = buildReportFilename(runId, section, "csv");
  return {
    blob: await response.blob(),
    filename: resolveDownloadFilename(response.headers.get("Content-Disposition"), fallback)
  };
}

export async function getReportPdf(runId: string): Promise<{ blob: Blob; filename: string }> {
  const response = await fetch(
    `${getApiBaseUrl()}/api/reports/${encodeURIComponent(runId)}/export.pdf`
  );
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  const fallback = buildReportFilename(runId, "report", "pdf");
  return {
    blob: await response.blob(),
    filename: resolveDownloadFilename(response.headers.get("Content-Disposition"), fallback)
  };
}

function buildQueryString(params: AnalysisRunListParams): string {
  const query = new URLSearchParams();
  if (params.status) {
    query.set("status", params.status);
  }
  if (params.video_id) {
    query.set("video_id", params.video_id);
  }
  if (params.limit !== undefined) {
    query.set("limit", String(params.limit));
  }
  if (params.offset !== undefined) {
    query.set("offset", String(params.offset));
  }
  const serialized = query.toString();
  return serialized ? `?${serialized}` : "";
}
