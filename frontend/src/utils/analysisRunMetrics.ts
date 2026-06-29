import type { AnalysisRunListResponse, AnalysisRunSummary } from "../types";

export const TRACKED_RUN_STATUSES = ["completed", "running", "failed", "unknown"] as const;

export const DASHBOARD_ARTIFACT_KEYS = [
  "detections",
  "tracks",
  "events",
  "alerts",
  "flow_counts",
  "zone_statistics"
] as const;

const ARTIFACT_STATUS_ALIASES: Record<string, readonly string[]> = {
  detections: ["detections", "detection_summary", "detections_csv", "detections_jsonl"],
  tracks: ["tracks", "tracking_summary", "tracks_csv", "tracks_jsonl"],
  trajectory_points: [
    "trajectory_points",
    "trajectory_summary",
    "trajectory_points_csv",
    "trajectory_points_jsonl"
  ]
};

export type TrackedRunStatus = (typeof TRACKED_RUN_STATUSES)[number];
export type ArtifactStatusCounts = Record<string, Record<string, number>>;

export interface AnalysisRunOverview {
  totalRuns: number;
  statusCounts: Record<TrackedRunStatus, number>;
  recentRuns: AnalysisRunSummary[];
}

export function buildAnalysisRunOverview(
  payload: AnalysisRunListResponse | AnalysisRunSummary[]
): AnalysisRunOverview {
  const runs = Array.isArray(payload) ? payload : payload.items;
  const totalRuns = Array.isArray(payload) ? runs.length : payload.total;
  const statusCounts = emptyStatusCounts();

  for (const run of runs) {
    statusCounts[toTrackedStatus(run.status)] += 1;
  }

  return {
    totalRuns,
    statusCounts,
    recentRuns: runs.slice(0, 5)
  };
}

export function buildArtifactStatusCounts(
  runs: AnalysisRunSummary[],
  artifactKeys: readonly string[] = DASHBOARD_ARTIFACT_KEYS
): ArtifactStatusCounts {
  const counts: ArtifactStatusCounts = {};

  for (const artifactKey of artifactKeys) {
    counts[artifactKey] = {};
    for (const run of runs) {
      const status = getArtifactStatus(run, artifactKey);
      counts[artifactKey][status] = (counts[artifactKey][status] ?? 0) + 1;
    }
  }

  return counts;
}

export function getArtifactStatus(run: AnalysisRunSummary, artifactKey: string): string {
  const artifactKeys = ARTIFACT_STATUS_ALIASES[artifactKey] ?? [artifactKey];
  const summaryStatuses = artifactKeys
    .map((currentKey) => getSummaryStatus(run, currentKey))
    .filter((status): status is string => Boolean(status));

  if (summaryStatuses.includes("available")) {
    return "available";
  }

  if (summaryStatuses.length > 0) {
    return (
      summaryStatuses.find((status) => status !== "missing") ??
      summaryStatuses[0]
    );
  }

  if (artifactKeys.some((currentKey) => run.artifact_paths?.[currentKey])) {
    return "available";
  }

  return "missing";
}

export function getRunId(run: AnalysisRunSummary): string {
  return run.run_id || run.id;
}

function emptyStatusCounts(): Record<TrackedRunStatus, number> {
  return {
    completed: 0,
    running: 0,
    failed: 0,
    unknown: 0
  };
}

function toTrackedStatus(status: string | undefined): TrackedRunStatus {
  if (status === "completed" || status === "running" || status === "failed") {
    return status;
  }
  return "unknown";
}

function getSummaryStatus(run: AnalysisRunSummary, artifactKey: string): string | undefined {
  const item = run.artifact_summary?.[artifactKey];
  if (!item) {
    return undefined;
  }
  if (item.available === true) {
    return "available";
  }
  return item.status;
}
