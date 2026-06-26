import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const outDir = path.join(tmpdir(), `smarttraffic-report-export-${process.pid}`);

rmSync(outDir, { force: true, recursive: true });
mkdirSync(outDir, { recursive: true });
writeFileSync(path.join(outDir, "package.json"), "{\"type\":\"module\"}\n");

execFileSync(
  path.join(repoRoot, "frontend/node_modules/.bin/tsc"),
  [
    path.join(repoRoot, "frontend/src/utils/reportExport.ts"),
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

const reportExport = await import(
  pathToFileURL(path.join(outDir, "utils/reportExport.js")).href
);

const summary = {
  run_id: "run.1",
  run: { id: "run.1", run_id: "run.1", status: "completed" },
  counts: {
    detections_count: 2,
    tracks_count: 1,
    trajectory_points_count: 3,
    events_count: 4,
    alerts_count: 5,
    flow_count_records: 6,
    zone_statistics_records: 7,
    bad_cases_count: 8,
    evaluation_results_count: 9
  },
  available_exports: ["events", "alerts"]
};

test("buildReportSummaryCards exposes export-focused counts", () => {
  assert.deepEqual(reportExport.buildReportSummaryCards(summary), [
    { label: "Events", value: 4 },
    { label: "Alerts", value: 5 },
    { label: "Flow records", value: 6 },
    { label: "Zone windows", value: 7 },
    { label: "Bad cases", value: 8 },
    { label: "Evaluation results", value: 9 }
  ]);
});

test("buildExportSectionOptions marks unavailable sections", () => {
  const options = reportExport.buildExportSectionOptions(["events"]);
  assert.equal(options.find((item) => item.key === "events").available, true);
  assert.equal(options.find((item) => item.key === "alerts").available, false);
});

test("JSON export preview and metadata are deterministic", () => {
  const payload = {
    metadata: {
      generated_at: "2026-01-01T00:00:00+00:00",
      schema_version: "full_stage_6ab.report.v1",
      note: reportExport.REPORT_NOT_FOR_ENFORCEMENT_WARNING,
      available_exports: ["events", "alerts"]
    },
    run: { id: "run.1", run_id: "run.1", status: "completed" },
    events: [],
    alerts: [],
    flow_counts: [],
    zone_statistics: [],
    bad_cases: [],
    evaluation_results: []
  };
  assert.match(reportExport.buildJsonExportPreview(payload), /full_stage_6ab\.report\.v1/);
  assert.deepEqual(reportExport.buildJsonExportMetadata(payload), [
    { label: "Schema", value: "full_stage_6ab.report.v1" },
    { label: "Generated", value: "2026-01-01T00:00:00+00:00" },
    { label: "Run", value: "run.1" },
    { label: "Sections", value: "events, alerts" }
  ]);
});

test("download filenames are safe and content disposition wins", () => {
  assert.equal(
    reportExport.buildReportFilename("run.1", "flow_counts", "csv"),
    "smarttraffic_run_1_flow_counts.csv"
  );
  assert.equal(
    reportExport.resolveDownloadFilename(
      'attachment; filename="smarttraffic_run_events.csv"',
      "fallback.csv"
    ),
    "smarttraffic_run_events.csv"
  );
});

test("empty state and enforcement warning stay explicit", () => {
  assert.equal(
    reportExport.buildEmptyReportState(null),
    "Select an analysis run to prepare report exports."
  );
  assert.match(reportExport.REPORT_NOT_FOR_ENFORCEMENT_WARNING, /not for traffic enforcement/);
});
