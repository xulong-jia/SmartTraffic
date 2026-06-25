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
          <h2>Dashboard</h2>
          <p>Analysis run status and artifact availability from the Stage 6 APIs.</p>
        </div>
      </header>
      {loading ? <p className="muted">Loading analysis runs...</p> : null}
      {error ? <p>{error}</p> : null}
      {overview ? (
        <>
          <MetricCards
            metrics={[
              { label: "Total runs", value: String(overview.totalRuns), detail: "indexed" },
              {
                label: "Completed",
                value: String(overview.statusCounts.completed),
                detail: "ready"
              },
              { label: "Running", value: String(overview.statusCounts.running), detail: "active" },
              { label: "Failed", value: String(overview.statusCounts.failed), detail: "needs check" },
              {
                label: "Unknown",
                value: String(overview.statusCounts.unknown),
                detail: "unclassified"
              }
            ]}
          />
          {runs.length === 0 ? (
            <section className="panel">
              <p className="muted">No analysis runs found.</p>
            </section>
          ) : (
            <div className="grid">
              <section className="panel">
                <h3>Artifact Status Summary</h3>
                <table>
                  <thead>
                    <tr>
                      <th>Artifact</th>
                      <th>Available</th>
                      <th>Missing</th>
                      <th>Planned</th>
                      <th>Empty</th>
                      <th>Missing source</th>
                      <th>Error</th>
                      <th>Other</th>
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
                <h3>Recent Analysis Runs</h3>
                <table>
                  <thead>
                    <tr>
                      <th>Run ID</th>
                      <th>Video ID</th>
                      <th>Status</th>
                      <th>Updated</th>
                      <th>Source</th>
                      {DASHBOARD_ARTIFACT_KEYS.map((artifactKey) => (
                        <th key={artifactKey}>{artifactKey}</th>
                      ))}
                      {onOpenAnalysisRun ? <th>Action</th> : null}
                    </tr>
                  </thead>
                  <tbody>
                    {overview.recentRuns.map((run) => (
                      <tr key={getRunId(run)}>
                        <td>{getRunId(run)}</td>
                        <td>{formatValue(run.video_id)}</td>
                        <td>{formatValue(run.status)}</td>
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
                              Open
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
