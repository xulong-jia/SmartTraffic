import { useEffect, useMemo, useState } from "react";

import {
  getReportBundle,
  getReportCsv,
  getReportJson,
  getReportPdf,
  getReportSummary,
  listReportRuns
} from "../api/reports";
import CollapsibleSection from "../components/CollapsibleSection";
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
      setSuccessMessage(`已下载 ${payload.filename}。`);
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
      setSuccessMessage(`已准备 ${filename}。`);
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
      setSuccessMessage(`已下载 ${payload.filename}。`);
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
      setSuccessMessage("报告包 metadata 已刷新。");
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
          <h2>报告中心</h2>
          <p>导出事件、告警、流量统计、坏例和评测报告。</p>
        </div>
        <button type="button" onClick={loadRuns} disabled={loading}>
          刷新
        </button>
      </header>

      <section className="panel report-toolbar-card">
        <div className="toolbar report-toolbar">
          <label>
            分析任务
            <select
              value={selectedRunId}
              onChange={(event) => {
                const runId = event.target.value;
                setSelectedRunId(runId);
                void loadSummary(runId);
              }}
            >
              <option value="">选择任务</option>
              {runs.map((run) => (
                <option key={run.run_id || run.id} value={run.run_id || run.id}>
                  {run.run_id || run.id}
                </option>
              ))}
            </select>
          </label>
          <button type="button" onClick={() => loadSummary()} disabled={loading || !selectedRunId}>
            加载摘要
          </button>
          <label>
            CSV 区块
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
            导出 CSV
          </button>
          <button
            type="button"
            onClick={exportJson}
            disabled={!summary || exporting !== null || !selectedRunId}
          >
            导出 JSON
          </button>
          <button
            type="button"
            onClick={exportPdf}
            disabled={!summary || exporting !== null || !selectedRunId}
          >
            导出 PDF
          </button>
          <button type="button" onClick={refreshBundle} disabled={!summary || loading}>
            Bundle 元数据
          </button>
        </div>
        <p className="warning-callout">{REPORT_NOT_FOR_ENFORCEMENT_WARNING}</p>
        {loading ? <p className="muted">正在加载报告数据...</p> : null}
        {error ? <p className="alert-box error">{error}</p> : null}
        {successMessage ? <p className="alert-box success">{successMessage}</p> : null}
        <p className="muted">{buildEmptyReportState(summary)}</p>
      </section>

      <section className="page-grid-2 report-summary-export-grid">
        <div className="panel card-fill report-summary-card">
          <div className="section-heading-row">
            <h3>摘要</h3>
            <span className="status-pill">{summary?.run.status || "无任务"}</span>
          </div>
          <div className="metric-row summary-grid report-summary-grid">
            {summaryCards.map((card) => {
              const label = splitMetricLabel(card.label);
              return (
                <div className="card metric-card" key={card.label}>
                  <span className="metric-value">{card.value}</span>
                  <span className={label.secondary ? "metric-label" : "muted"}>
                    {label.primary}
                  </span>
                  {label.secondary ? (
                    <span className="metric-subvalue">{label.secondary}</span>
                  ) : null}
                </div>
              );
            })}
          </div>
          <dl className="detail-grid">
            <div>
              <dt>Run ID</dt>
              <dd>{summary?.run_id || selectedRunId || "-"}</dd>
            </div>
            <div>
              <dt>来源</dt>
              <dd>{summary?.run.source || "-"}</dd>
            </div>
            <div>
              <dt>视频</dt>
              <dd>{summary?.run.video_id || "-"}</dd>
            </div>
          </dl>
        </div>

        <div className="panel table-section card-fill report-export-card">
          <div className="section-heading-row">
            <h3>导出区块</h3>
            <span className="status-pill">{sectionOptions.length} 个区块</span>
          </div>
          <div className="table-scroll">
            <table className="data-table">
              <caption className="sr-only">报告导出区块可用性</caption>
              <thead>
                <tr>
                  <th scope="col">区块</th>
                  <th scope="col">说明</th>
                  <th scope="col">状态</th>
                </tr>
              </thead>
              <tbody>
                {sectionOptions.map((section) => (
                  <tr key={section.key}>
                    <td>{section.label}</td>
                    <td>{section.description}</td>
                    <td>
                      <span className={`status-pill ${section.available ? "status-available" : "status-empty"}`}>
                        {section.available ? "可用" : "不可用"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <CollapsibleSection title="报告明细" className="report-detail-section">
        <section className="report-metadata-stack">
          <div className="panel report-metadata-card">
            <h3>报告指标</h3>
            <dl className="detail-grid">
              <div>
                <dt>主要事件</dt>
                <dd>{formatDisplayValue(summary?.top_event_types)}</dd>
              </div>
              <div>
                <dt>告警状态</dt>
                <dd>{formatDisplayValue(summary?.alert_status_counts)}</dd>
              </div>
              <div>
                <dt>流量总计</dt>
                <dd>{formatDisplayValue(summary?.flow_totals)}</dd>
              </div>
              <div>
                <dt>坏例状态</dt>
                <dd>{formatDisplayValue(summary?.bad_case_status_counts)}</dd>
              </div>
              <div>
                <dt>结果目录</dt>
                <dd className="cell-path">{summary?.run.result_dir || "-"}</dd>
              </div>
            </dl>
          </div>

          <div className="panel report-metadata-card">
            <h3>JSON 预览</h3>
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
              <p className="muted">导出 JSON 后可预览完整结构化报告。</p>
            )}
            {jsonPreview ? <pre className="json-panel">{jsonPreview}</pre> : null}
          </div>
        </section>
      </CollapsibleSection>

      <CollapsibleSection title="产物引用与可视化明细" className="report-detail-section">
        <section className="report-metadata-stack report-artifact-stack">
          <div className="panel table-section table-card report-bundle-card">
            <div className="section-heading-row">
              <h3>报告包</h3>
              <span className="status-pill">{activeBundle?.schema_version || "无 bundle"}</span>
            </div>
            <p className="muted">{buildBundleSectionLabel(activeBundle)}</p>
            <div className="table-scroll">
              <table className="data-table">
                <caption className="sr-only">报告包产物引用</caption>
                <thead>
                  <tr>
                    <th scope="col">产物</th>
                    <th scope="col">类型</th>
                    <th scope="col">状态</th>
                    <th scope="col">路径</th>
                  </tr>
                </thead>
                <tbody>
                  {artifactRows.length ? (
                    artifactRows.map((row) => (
                      <tr key={row.key}>
                        <td>{row.key}</td>
                        <td>{row.type}</td>
                        <td>{row.status}</td>
                        <td className="cell-path">{row.path}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={4}>暂无 bundle metadata。</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="panel table-section table-card report-visual-card">
            <div className="section-heading-row">
              <h3>可视化产物摘要</h3>
              <span className="status-pill">{summary?.keyframe_summary.status || "无任务"}</span>
            </div>
            <dl className="detail-grid">
              <div>
                <dt>关键帧</dt>
                <dd>
                  {summary
                    ? `${summary.keyframe_summary.keyframe_count} 项（${summary.keyframe_summary.status}）`
                    : "-"}
                </dd>
              </div>
              <div>
                <dt>标注视频</dt>
                <dd className="cell-path">{annotatedVideoLabel}</dd>
              </div>
            </dl>
            <div className="table-scroll">
              <table className="data-table">
                <caption className="sr-only">关键帧产物引用</caption>
                <thead>
                  <tr>
                    <th scope="col">来源</th>
                    <th scope="col">帧</th>
                    <th scope="col">状态</th>
                    <th scope="col">路径</th>
                  </tr>
                </thead>
                <tbody>
                  {keyframeRows.length ? (
                    keyframeRows.map((row) => (
                      <tr key={`${row.source}-${row.frame}-${row.path}`}>
                        <td>{row.source}</td>
                        <td>{row.frame}</td>
                        <td>{row.status}</td>
                        <td className="cell-path">{row.path}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={4}>暂无关键帧引用。</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </CollapsibleSection>
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

function splitMetricLabel(label: string): { primary: string; secondary: string } {
  const [primary, ...rest] = label.split(" ");
  return { primary, secondary: rest.join(" ") };
}
