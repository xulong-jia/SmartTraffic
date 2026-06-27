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
          <h2>总览 Dashboard</h2>
          <p>查看分析任务状态、结果产物和系统运行概况。</p>
        </div>
      </header>
      {loading ? <p className="muted">正在加载分析任务...</p> : null}
      {error ? <p>{error}</p> : null}
      {overview ? (
        <>
          <MetricCards
            metrics={[
              { label: "总分析数", value: String(overview.totalRuns), detail: "已索引 indexed" },
              {
                label: "已完成",
                value: String(overview.statusCounts.completed),
                detail: "可查看 ready"
              },
              {
                label: "运行中",
                value: String(overview.statusCounts.running),
                detail: "处理中 active"
              },
              {
                label: "失败",
                value: String(overview.statusCounts.failed),
                detail: "需检查 needs check"
              },
              {
                label: "未知",
                value: String(overview.statusCounts.unknown),
                detail: "未分类 unclassified"
              }
            ]}
          />
          {runs.length === 0 ? (
            <section className="panel">
              <p className="muted">暂无分析任务。请先在视频中心上传视频并启动分析。</p>
            </section>
          ) : (
            <div className="grid">
              <section className="panel">
                <h3>产物状态汇总 Artifact Status</h3>
                <table>
                  <thead>
                    <tr>
                      <th>产物 Artifact</th>
                      <th>可用 Available</th>
                      <th>缺失 Missing</th>
                      <th>计划中 Planned</th>
                      <th>为空 Empty</th>
                      <th>缺少来源 Missing source</th>
                      <th>错误 Error</th>
                      <th>其他 Other</th>
                    </tr>
                  </thead>
                  <tbody>
                    {DASHBOARD_ARTIFACT_KEYS.map((artifactKey) => (
                      <tr key={artifactKey}>
                        <td>{artifactKey}</td>
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
              </section>
              <section className="panel">
                <h3>最近分析任务 Recent Analysis Runs</h3>
                <table>
                  <thead>
                    <tr>
                      <th>Run ID</th>
                      <th>Video ID</th>
                      <th>状态 Status</th>
                      <th>更新时间 Updated</th>
                      <th>来源 Source</th>
                      {DASHBOARD_ARTIFACT_KEYS.map((artifactKey) => (
                        <th key={artifactKey}>{artifactKey}</th>
                      ))}
                      {onOpenAnalysisRun ? <th>操作 Action</th> : null}
                    </tr>
                  </thead>
                  <tbody>
                    {overview.recentRuns.map((run) => (
                      <tr key={getRunId(run)}>
                        <td>{getRunId(run)}</td>
                        <td>{formatValue(run.video_id)}</td>
                        <td>
                          <span className={`status-pill status-${statusClassName(run.status)}`}>
                            {formatStatusValue(run.status)}
                          </span>
                        </td>
                        <td>{formatValue(run.updated_at || run.finished_at)}</td>
                        <td>{formatValue(run.source)}</td>
                        {DASHBOARD_ARTIFACT_KEYS.map((artifactKey) => (
                          <td key={artifactKey}>
                            <span className={`status-pill status-${getArtifactStatus(run, artifactKey)}`}>
                              {getArtifactStatus(run, artifactKey)}
                            </span>
                          </td>
                        ))}
                        {onOpenAnalysisRun ? (
                          <td>
                            <button type="button" onClick={() => onOpenAnalysisRun(getRunId(run))}>
                              打开 Open
                            </button>
                          </td>
                        ) : null}
                      </tr>
                    ))}
                  </tbody>
                </table>
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
    completed: "已完成 completed",
    running: "运行中 running",
    failed: "失败 failed",
    pending: "待处理 pending"
  };
  return labels[raw] ?? raw;
}

function statusClassName(value: AnalysisRunSummary[keyof AnalysisRunSummary]): string {
  const raw = formatValue(value).toLowerCase().replace(/[^a-z0-9_-]+/g, "_");
  return raw || "unknown";
}
