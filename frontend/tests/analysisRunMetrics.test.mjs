import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const outDir = path.join(tmpdir(), `smarttraffic-analysis-run-metrics-${process.pid}`);

rmSync(outDir, { force: true, recursive: true });
mkdirSync(outDir, { recursive: true });
writeFileSync(path.join(outDir, "package.json"), "{\"type\":\"module\"}\n");

execFileSync(
  path.join(repoRoot, "frontend/node_modules/.bin/tsc"),
  [
    path.join(repoRoot, "frontend/src/utils/analysisRunMetrics.ts"),
    path.join(repoRoot, "frontend/src/utils/format.ts"),
    "--outDir",
    outDir,
    "--module",
    "ES2022",
    "--moduleResolution",
    "Bundler",
    "--target",
    "ES2022",
    "--skipLibCheck",
    "--esModuleInterop",
    "--declaration",
    "false",
    "--sourceMap",
    "false"
  ],
  { stdio: "pipe" }
);

const metrics = await import(pathToFileURL(path.join(outDir, "utils/analysisRunMetrics.js")).href);
const format = await import(pathToFileURL(path.join(outDir, "utils/format.js")).href);

test("buildAnalysisRunOverview counts Stage 6D list totals and status buckets", () => {
  const overview = metrics.buildAnalysisRunOverview({
    total: 4,
    limit: 50,
    offset: 0,
    items: [
      { id: "run-a", run_id: "run-a", status: "completed" },
      { id: "run-b", run_id: "run-b", status: "running" },
      { id: "run-c", run_id: "run-c", status: "failed" },
      { id: "run-d", run_id: "run-d", status: "paused" }
    ]
  });

  assert.equal(overview.totalRuns, 4);
  assert.deepEqual(overview.statusCounts, {
    completed: 1,
    running: 1,
    failed: 1,
    unknown: 1
  });
});

test("getArtifactStatus prefers artifact_summary and falls back to paths", () => {
  const run = {
    id: "run-a",
    run_id: "run-a",
    status: "completed",
    artifact_paths: {
      tracks: "tracks.jsonl"
    },
    artifact_summary: {
      detections: { status: "available", path: "detections.jsonl", record_count: 12 },
      flow_counts: { status: "planned", path: "flow_counts.json", record_count: 0 }
    }
  };

  assert.equal(metrics.getArtifactStatus(run, "detections"), "available");
  assert.equal(metrics.getArtifactStatus(run, "flow_counts"), "planned");
  assert.equal(metrics.getArtifactStatus(run, "tracks"), "available");
  assert.equal(metrics.getArtifactStatus(run, "alerts"), "missing");
});

test("getArtifactStatus resolves dashboard artifact aliases from detailed artifact keys", () => {
  const run = {
    id: "run_50007c86fd60",
    run_id: "run_50007c86fd60",
    status: "completed",
    artifact_summary: {
      detection_summary: { status: "available", path: "detection_summary.json", record_count: 1 },
      detections_csv: { status: "missing", path: "detections.csv", record_count: 0 },
      detections_jsonl: { status: "available", path: "detections.jsonl", record_count: 120 },
      tracking_summary: { available: true, path: "tracking_summary.json", record_count: 1 },
      tracks_csv: { status: "available", path: "tracks.csv", record_count: 6483 },
      trajectory_summary: { status: "available", path: "trajectory_summary.json", record_count: 1 },
      trajectory_points_jsonl: {
        status: "available",
        path: "trajectory_points.jsonl",
        record_count: 120
      }
    }
  };

  assert.equal(metrics.getArtifactStatus(run, "detections"), "available");
  assert.equal(metrics.getArtifactStatus(run, "tracks"), "available");
  assert.equal(metrics.getArtifactStatus(run, "trajectory_points"), "available");
});

test("buildArtifactStatusCounts summarizes selected artifact availability", () => {
  const counts = metrics.buildArtifactStatusCounts(
    [
      {
        id: "run-a",
        run_id: "run-a",
        status: "completed",
        artifact_summary: {
          events: { status: "available", path: "events.jsonl", record_count: 2 },
          alerts: { status: "missing", path: "alerts.jsonl", record_count: 0 },
          keyframes: { status: "empty", path: "keyframes/", record_count: 0 }
        }
      },
      {
        id: "run-b",
        run_id: "run-b",
        status: "completed",
        artifact_summary: {
          events: { status: "error", path: "events.jsonl", record_count: 0 },
          alerts: { status: "available", path: "alerts.jsonl", record_count: 3 },
          keyframes: {
            status: "missing_source_video",
            path: "keyframes/index.json",
            record_count: 0
          }
        }
      }
    ],
    ["events", "alerts", "keyframes"]
  );

  assert.deepEqual(counts, {
    events: { available: 1, error: 1 },
    alerts: { missing: 1, available: 1 },
    keyframes: { empty: 1, missing_source_video: 1 }
  });
});

test("formatDisplayValue avoids undefined text in empty metric summaries", () => {
  assert.equal(format.formatDisplayValue(undefined), "-");
  assert.equal(format.formatDisplayValue(null), "-");
  assert.equal(format.formatDisplayValue("", "0"), "0");
  assert.equal(format.formatDisplayValue(undefined, "0"), "0");
  assert.equal(format.formatDisplayValue(12), "12");
  assert.equal(format.formatDisplayValue(Number.NaN), "-");
  assert.equal(format.formatDisplayValue({ status: "empty" }), "{\"status\":\"empty\"}");
});
