import { useEffect, useState } from "react";

import { listAnalysisRuns } from "../api/analysisRuns";
import MetricCards from "../components/MetricCards";
import type { AnalysisRunListResponse, AnalysisRunSummary } from "../types";
import {
  DASHBOARD_ARTIFACT_KEYS,
  buildAnalysisRunOverview,
  buildArtifactStatusCounts,
  getArtifactStatus,
  getRunId
} from "../utils/analysisRunMetrics";

interface DashboardPageProps {
  onOpenAnalysisRun?: (runId: string) => void;
}

export default function DashboardPage({ onOpenAnalysisRun }: DashboardPageProps) {
  const [runsResponse, setRunsResponse] = useState<AnalysisRunListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    listAnalysisRuns({ limit: 50 })
      .then(setRunsResponse)
      .catch((currentError: Error) => setError(currentError.message))
      .finally(() => setLoading(false));
  }, []);

  const overview = runsResponse ? buildAnalysisRunOverview(runsResponse) : null;
  const runs = runsResponse?.items ?? [];
  const artifactCounts = buildArtifactStatusCounts(runs);

  return (
    <>
      <header className="page-header">
        <div>
          <h2>总览</h2>
          <p>查看分析任务状态、结果产物和系统运行概况。</p>
        </div>
      </header>
      {loading ? <p className="muted">正在加载分析任务...</p> : null}
      {error ? <p>{error}</p> : null}
      {overview ? (
        <>
          <MetricCards
            metrics={[
              { label: "总分析数", value: String(overview.totalRuns), detail: "已索引" },
              {
                label: "已完成",
                value: String(overview.statusCounts.completed),
                detail: "可查看"
              },
              {
                label: "运行中",
                value: String(overview.statusCounts.running),
                detail: "处理中"
              },
              {
                label: "失败",
                value: String(overview.statusCounts.failed),
                detail: "需检查"
              },
              {
                label: "未知",
                value: String(overview.statusCounts.unknown),
                detail: "未分类"
              }
            ]}
          />
          {runs.length === 0 ? (
            <section className="panel">
              <p className="empty-state">暂无分析任务。请先在视频中心上传视频并启动分析。</p>
            </section>
          ) : (
            <div className="grid content-grid">
              <section className="panel">
                <h3>产物状态汇总</h3>
                <div className="table-scroll">
                  <table className="data-table dashboard-table">
                    <thead>
                      <tr>
                        <th>产物</th>
                        <th>可用</th>
                        <th>缺失</th>
                        <th>计划中</th>
                        <th>为空</th>
                        <th>缺少源视频</th>
                        <th>错误</th>
                        <th>其他</th>
                      </tr>
                    </thead>
                    <tbody>
                      {DASHBOARD_ARTIFACT_KEYS.map((artifactKey) => (
                        <tr key={artifactKey}>
                          <td>{artifactLabel(artifactKey)}</td>
                          <td>{formatCount(artifactCounts[artifactKey]?.available)}</td>
                          <td>{formatCount(artifactCounts[artifactKey]?.missing)}</td>
                          <td>{formatCount(artifactCounts[artifactKey]?.planned)}</td>
                          <td>{formatCount(artifactCounts[artifactKey]?.empty)}</td>
                          <td>{formatCount(artifactCounts[artifactKey]?.missing_source_video)}</td>
                          <td>{formatCount(artifactCounts[artifactKey]?.error)}</td>
                          <td>{formatOtherStatusCount(artifactCounts[artifactKey])}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
              <section className="panel">
                <h3>最近分析任务</h3>
                <div className="table-scroll">
                  <table className="data-table dashboard-table">
                    <thead>
                      <tr>
                        <th>任务</th>
                        <th>视频</th>
                        <th>状态</th>
                        <th>更新时间</th>
                        <th>来源</th>
                        {DASHBOARD_ARTIFACT_KEYS.map((artifactKey) => (
                          <th key={artifactKey}>{artifactLabel(artifactKey)}</th>
                        ))}
                        {onOpenAnalysisRun ? <th>操作</th> : null}
                      </tr>
                    </thead>
                    <tbody>
                      {overview.recentRuns.map((run) => (
                        <tr key={getRunId(run)}>
                          <td className="cell-id">{getRunId(run)}</td>
                          <td className="cell-id">{formatValue(run.video_id)}</td>
                          <td>
                            <span className={`status-pill status-${statusClassName(run.status)}`}>
                              {formatStatusValue(run.status)}
                            </span>
                          </td>
                          <td>{formatValue(run.updated_at || run.finished_at)}</td>
                          <td>{formatValue(run.source)}</td>
                          {DASHBOARD_ARTIFACT_KEYS.map((artifactKey) => {
                            const status = getArtifactStatus(run, artifactKey);
                            return (
                              <td key={artifactKey}>
                                <span className={`status-pill status-${status}`}>
                                  {formatArtifactStatusValue(status)}
                                </span>
                              </td>
                            );
                          })}
                          {onOpenAnalysisRun ? (
                            <td>
                              <button type="button" onClick={() => onOpenAnalysisRun(getRunId(run))}>
                                打开
                              </button>
                            </td>
                          ) : null}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            </div>
          )}
        </>
      ) : null}
    </>
  );
}

function formatCount(value: number | undefined): string {
  return String(value ?? 0);
}

function formatOtherStatusCount(counts: Record<string, number> | undefined): string {
  if (!counts) {
    return "0";
  }
  const known = new Set([
    "available",
    "missing",
    "planned",
    "empty",
    "missing_source_video",
    "error"
  ]);
  const total = Object.entries(counts)
    .filter(([status]) => !known.has(status))
    .reduce((sum, [, count]) => sum + count, 0);
  return String(total);
}

function formatValue(value: AnalysisRunSummary[keyof AnalysisRunSummary]): string {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return String(value);
}

function formatStatusValue(value: AnalysisRunSummary[keyof AnalysisRunSummary]): string {
  const raw = formatValue(value);
  const labels: Record<string, string> = {
    completed: "已完成",
    running: "运行中",
    failed: "失败",
    pending: "待处理"
  };
  return labels[raw] ?? raw;
}

function formatArtifactStatusValue(value: string): string {
  const labels: Record<string, string> = {
    available: "可用",
    missing: "缺失",
    planned: "计划中",
    empty: "为空",
    missing_source_video: "缺少源视频",
    error: "错误"
  };
  return labels[value] ?? value;
}

function statusClassName(value: AnalysisRunSummary[keyof AnalysisRunSummary]): string {
  const raw = formatValue(value).toLowerCase().replace(/[^a-z0-9_-]+/g, "_");
  return raw || "unknown";
}

function artifactLabel(value: string): string {
  const labels: Record<string, string> = {
    detections: "检测",
    tracks: "跟踪",
    events: "事件",
    alerts: "告警",
    flow_counts: "流量",
    zone_statistics: "区域"
  };
  return labels[value] ?? value;
}
