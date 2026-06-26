import { useEffect, useMemo, useState } from "react";

import {
  getReportBundle,
  getReportCsv,
  getReportJson,
  getReportPdf,
  getReportSummary,
  listReportRuns
} from "../api/reports";
import type {
  AnalysisRunSummary,
  ReportBundleResponse,
  ReportExportSection,
  ReportJsonExportResponse,
  ReportSummaryResponse
} from "../types";
import { formatDisplayValue } from "../utils/format";
import {
  REPORT_NOT_FOR_ENFORCEMENT_WARNING,
  buildEmptyReportState,
  buildAnnotatedVideoLabel,
  buildArtifactReferenceRows,
  buildBundleSectionLabel,
  buildExportSectionOptions,
  buildJsonExportMetadata,
  buildJsonExportPreview,
  buildKeyframeSummaryRows,
  buildReportFilename,
  buildReportSummaryCards
} from "../utils/reportExport";

export default function ReportCenterPage() {
  const [runs, setRuns] = useState<AnalysisRunSummary[]>([]);
  const [selectedRunId, setSelectedRunId] = useState("");
  const [summary, setSummary] = useState<ReportSummaryResponse | null>(null);
  const [bundle, setBundle] = useState<ReportBundleResponse | null>(null);
  const [jsonExport, setJsonExport] = useState<ReportJsonExportResponse | null>(null);
  const [selectedSection, setSelectedSection] = useState<ReportExportSection>("events");
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState<ReportExportSection | "json" | "pdf" | null>(null);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const summaryCards = buildReportSummaryCards(summary);
  const sectionOptions = useMemo(
    () => buildExportSectionOptions(summary?.available_exports),
    [summary?.available_exports]
  );
  const jsonMetadata = buildJsonExportMetadata(jsonExport);
  const jsonPreview = buildJsonExportPreview(jsonExport);
  const activeBundle = bundle || summary?.bundle || null;
  const artifactRows = buildArtifactReferenceRows(activeBundle);
  const keyframeRows = buildKeyframeSummaryRows(summary?.keyframe_summary ?? null);
  const annotatedVideoLabel = buildAnnotatedVideoLabel(summary?.annotated_video ?? null);

  useEffect(() => {
    void loadRuns();
  }, []);

  async function loadRuns() {
    setLoading(true);
    setError("");
    setSuccessMessage("");
    try {
      const payload = await listReportRuns({ limit: 100, offset: 0 });
      setRuns(payload.items);
      const nextRunId = selectedRunId || payload.items[0]?.run_id || payload.items[0]?.id || "";
      setSelectedRunId(nextRunId);
      if (nextRunId) {
        await loadSummary(nextRunId);
      } else {
        setSummary(null);
        setBundle(null);
        setJsonExport(null);
      }
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Report runs request failed");
    } finally {
      setLoading(false);
    }
  }

  async function loadSummary(runId = selectedRunId) {
    const normalizedRunId = runId.trim();
    if (!normalizedRunId) {
      setSummary(null);
      setJsonExport(null);
      return;
    }
    setLoading(true);
    setError("");
    setSuccessMessage("");
    try {
      const payload = await getReportSummary(normalizedRunId);
      setSummary(payload);
      setBundle(payload.bundle);
      setJsonExport(null);
      const nextSection = buildExportSectionOptions(payload.available_exports).find(
        (item) => item.available
      )?.key;
      if (nextSection) {
        setSelectedSection(nextSection);
      }
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Report summary request failed");
      setSummary(null);
      setBundle(null);
      setJsonExport(null);
    } finally {
      setLoading(false);
    }
  }

  async function exportCsv() {
    if (!selectedRunId) {
      setError("run_id is required.");
      return;
    }
    setExporting(selectedSection);
    setError("");
    setSuccessMessage("");
    try {
      const payload = await getReportCsv(selectedRunId, selectedSection);
      triggerDownload(payload.blob, payload.filename);
      setSuccessMessage(`Downloaded ${payload.filename}.`);
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "CSV export failed");
    } finally {
      setExporting(null);
    }
  }

  async function exportJson() {
    if (!selectedRunId) {
      setError("run_id is required.");
      return;
    }
    setExporting("json");
    setError("");
    setSuccessMessage("");
    try {
      const payload = await getReportJson(selectedRunId);
      setJsonExport(payload);
      const filename = buildReportFilename(selectedRunId, "full_report", "json");
      triggerDownload(
        new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }),
        filename
      );
      setSuccessMessage(`Prepared ${filename}.`);
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "JSON export failed");
    } finally {
      setExporting(null);
    }
  }

  async function exportPdf() {
    if (!selectedRunId) {
      setError("run_id is required.");
      return;
    }
    setExporting("pdf");
    setError("");
    setSuccessMessage("");
    try {
      const payload = await getReportPdf(selectedRunId);
      triggerDownload(payload.blob, payload.filename);
      setSuccessMessage(`Downloaded ${payload.filename}.`);
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "PDF export failed");
    } finally {
      setExporting(null);
    }
  }

  async function refreshBundle() {
    if (!selectedRunId) {
      setError("run_id is required.");
      return;
    }
    setLoading(true);
    setError("");
    setSuccessMessage("");
    try {
      setBundle(await getReportBundle(selectedRunId));
      setSuccessMessage("Bundle metadata refreshed.");
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Bundle request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <header className="page-header">
        <div>
          <h2>Report Center</h2>
          <p>CSV / JSON exports for completed analysis, review, bad case, and evaluation data.</p>
        </div>
        <button type="button" onClick={loadRuns} disabled={loading}>
          Refresh
        </button>
      </header>

      <section className="panel">
        <div className="toolbar">
          <label>
            Analysis run
            <select
              value={selectedRunId}
              onChange={(event) => {
                const runId = event.target.value;
                setSelectedRunId(runId);
                void loadSummary(runId);
              }}
            >
              <option value="">Select run</option>
              {runs.map((run) => (
                <option key={run.run_id || run.id} value={run.run_id || run.id}>
                  {run.run_id || run.id}
                </option>
              ))}
            </select>
          </label>
          <button type="button" onClick={() => loadSummary()} disabled={loading || !selectedRunId}>
            Load summary
          </button>
          <label>
            CSV section
            <select
              value={selectedSection}
              onChange={(event) => setSelectedSection(event.target.value as ReportExportSection)}
              disabled={!summary}
            >
              {sectionOptions.map((section) => (
                <option key={section.key} value={section.key} disabled={!section.available}>
                  {section.label}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            onClick={exportCsv}
            disabled={!summary || exporting !== null || !selectedRunId}
          >
            Export CSV
          </button>
          <button
            type="button"
            onClick={exportJson}
            disabled={!summary || exporting !== null || !selectedRunId}
          >
            Export JSON
          </button>
          <button
            type="button"
            onClick={exportPdf}
            disabled={!summary || exporting !== null || !selectedRunId}
          >
            Export PDF
          </button>
          <button type="button" onClick={refreshBundle} disabled={!summary || loading}>
            Bundle
          </button>
        </div>
        <p className="muted">{REPORT_NOT_FOR_ENFORCEMENT_WARNING}</p>
        {loading ? <p className="muted">Loading report data</p> : null}
        {error ? <p className="status-pill status-error">{error}</p> : null}
        {successMessage ? <p className="status-pill status-available">{successMessage}</p> : null}
        <p className="muted">{buildEmptyReportState(summary)}</p>
      </section>

      <section className="grid two">
        <div className="panel">
          <div className="section-heading-row">
            <h3>Summary</h3>
            <span className="status-pill">{summary?.run.status || "No run"}</span>
          </div>
          <div className="metric-row">
            {summaryCards.map((card) => (
              <div className="card metric-card" key={card.label}>
                <span className="metric-value">{card.value}</span>
                <span className="muted">{card.label}</span>
              </div>
            ))}
          </div>
          <dl className="detail-grid">
            <div>
              <dt>Run ID</dt>
              <dd>{summary?.run_id || selectedRunId || "-"}</dd>
            </div>
            <div>
              <dt>Source</dt>
              <dd>{summary?.run.source || "-"}</dd>
            </div>
            <div>
              <dt>Video</dt>
              <dd>{summary?.run.video_id || "-"}</dd>
            </div>
            <div>
              <dt>Result dir</dt>
              <dd>{summary?.run.result_dir || "-"}</dd>
            </div>
          </dl>
        </div>

        <div className="panel">
          <div className="section-heading-row">
            <h3>Export Sections</h3>
            <span className="status-pill">{sectionOptions.length} sections</span>
          </div>
          <table>
            <thead>
              <tr>
                <th>Section</th>
                <th>Description</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {sectionOptions.map((section) => (
                <tr key={section.key}>
                  <td>{section.label}</td>
                  <td>{section.description}</td>
                  <td>
                    <span className={`status-pill ${section.available ? "status-available" : "status-empty"}`}>
                      {section.available ? "Available" : "Unavailable"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="grid two">
        <div className="panel">
          <h3>Report Metrics</h3>
          <dl className="detail-grid">
            <div>
              <dt>Top events</dt>
              <dd>{formatDisplayValue(summary?.top_event_types)}</dd>
            </div>
            <div>
              <dt>Alert statuses</dt>
              <dd>{formatDisplayValue(summary?.alert_status_counts)}</dd>
            </div>
            <div>
              <dt>Flow totals</dt>
              <dd>{formatDisplayValue(summary?.flow_totals)}</dd>
            </div>
            <div>
              <dt>Bad case statuses</dt>
              <dd>{formatDisplayValue(summary?.bad_case_status_counts)}</dd>
            </div>
          </dl>
        </div>

        <div className="panel">
          <h3>JSON Preview</h3>
          {jsonMetadata.length ? (
            <dl className="detail-grid">
              {jsonMetadata.map((item) => (
                <div key={item.label}>
                  <dt>{item.label}</dt>
                  <dd>{item.value}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="muted">Export JSON to preview the full structured report.</p>
          )}
          {jsonPreview ? <pre className="json-panel">{jsonPreview}</pre> : null}
        </div>
      </section>

      <section className="grid two">
        <div className="panel">
          <div className="section-heading-row">
            <h3>Report Bundle</h3>
            <span className="status-pill">{activeBundle?.schema_version || "No bundle"}</span>
          </div>
          <p className="muted">{buildBundleSectionLabel(activeBundle)}</p>
          <table>
            <thead>
              <tr>
                <th>Artifact</th>
                <th>Type</th>
                <th>Status</th>
                <th>Path</th>
              </tr>
            </thead>
            <tbody>
              {artifactRows.length ? (
                artifactRows.map((row) => (
                  <tr key={row.key}>
                    <td>{row.key}</td>
                    <td>{row.type}</td>
                    <td>{row.status}</td>
                    <td>{row.path}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4}>No bundle metadata loaded.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="panel">
          <div className="section-heading-row">
            <h3>Visual Artifact Summary</h3>
            <span className="status-pill">{summary?.keyframe_summary.status || "No run"}</span>
          </div>
          <dl className="detail-grid">
            <div>
              <dt>Keyframes</dt>
              <dd>
                {summary
                  ? `${summary.keyframe_summary.keyframe_count} items (${summary.keyframe_summary.status})`
                  : "-"}
              </dd>
            </div>
            <div>
              <dt>Annotated video</dt>
              <dd>{annotatedVideoLabel}</dd>
            </div>
          </dl>
          <table>
            <thead>
              <tr>
                <th>Source</th>
                <th>Frame</th>
                <th>Status</th>
                <th>Path</th>
              </tr>
            </thead>
            <tbody>
              {keyframeRows.length ? (
                keyframeRows.map((row) => (
                  <tr key={`${row.source}-${row.frame}-${row.path}`}>
                    <td>{row.source}</td>
                    <td>{row.frame}</td>
                    <td>{row.status}</td>
                    <td>{row.path}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4}>No keyframe item references available.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
