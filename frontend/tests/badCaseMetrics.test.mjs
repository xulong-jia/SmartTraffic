import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const outDir = path.join(tmpdir(), `smarttraffic-bad-case-metrics-${process.pid}`);

rmSync(outDir, { force: true, recursive: true });
mkdirSync(outDir, { recursive: true });
writeFileSync(path.join(outDir, "package.json"), "{\"type\":\"module\"}\n");

execFileSync(
  path.join(repoRoot, "frontend/node_modules/.bin/tsc"),
  [
    path.join(repoRoot, "frontend/src/utils/badCaseMetrics.ts"),
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

const badCaseMetrics = await import(
  pathToFileURL(path.join(outDir, "utils/badCaseMetrics.js")).href
);

const cases = [
  {
    case_id: "badcase_a",
    run_id: "run_a",
    case_type: "false_positive",
    module: "event_engine",
    status: "open",
    source: "manual",
    tags: ["wrong_way", "threshold"],
    updated_at: "2026-01-01T00:00:00+00:00"
  },
  {
    case_id: "badcase_b",
    run_id: "run_a",
    case_type: "tracking_fragmentation",
    module: "tracker",
    status: "fixed",
    source: "review_center",
    tags: ["identity"],
    updated_at: "2026-01-02T00:00:00+00:00"
  },
  {
    case_id: "badcase_c",
    run_id: "run_b",
    case_type: "unexpected_type",
    module: "unexpected_module",
    status: "unexpected_status",
    source: "manual",
    tags: ["wrong_way", ""],
    updated_at: "2026-01-03T00:00:00+00:00"
  }
];

test("buildBadCaseStatusCounts counts known statuses and unknown fallback", () => {
  assert.deepEqual(badCaseMetrics.buildBadCaseStatusCounts(cases), {
    open: 1,
    triaged: 0,
    fixed: 1,
    verified: 0,
    wont_fix: 0,
    unknown: 1
  });
});

test("buildBadCaseTypeCounts and module counts include unknown fallback", () => {
  assert.deepEqual(badCaseMetrics.buildBadCaseTypeCounts(cases), {
    false_positive: 1,
    false_negative: 0,
    detection_miss: 0,
    detection_false_positive: 0,
    tracking_fragmentation: 1,
    id_switch: 0,
    trajectory_error: 0,
    event_rule_error: 0,
    annotation_error: 0,
    other: 0,
    unknown: 1
  });
  assert.deepEqual(badCaseMetrics.buildBadCaseModuleCounts(cases), {
    detector: 0,
    tracker: 1,
    trajectory: 0,
    event_engine: 1,
    review_center: 0,
    visualization: 0,
    other: 0,
    unknown: 1
  });
});

test("normalizeBadCaseTags removes blanks and trims values", () => {
  assert.deepEqual(
    badCaseMetrics.normalizeBadCaseTags([" wrong_way ", "", "threshold"]),
    ["wrong_way", "threshold"]
  );
  assert.deepEqual(badCaseMetrics.normalizeBadCaseTags(" wrong_way, threshold ,, "), [
    "wrong_way",
    "threshold"
  ]);
});

test("formatBadCaseStatusLabel keeps compact labels", () => {
  assert.equal(badCaseMetrics.formatBadCaseStatusLabel("open"), "未处理 open");
  assert.equal(badCaseMetrics.formatBadCaseStatusLabel("wont_fix"), "暂不修复 wont_fix");
  assert.equal(badCaseMetrics.formatBadCaseStatusLabel("unexpected_status"), "unexpected_status");
});

test("buildBadCaseDisplaySummary normalizes optional fields", () => {
  assert.deepEqual(
    badCaseMetrics.buildBadCaseDisplaySummary({
      case_id: "badcase_a",
      run_id: "run_a",
      case_type: "false_positive",
      module: "event_engine",
      status: "open",
      source: "manual",
      linked_failed_case_id: "failed_eval_1",
      event_id: "",
      track_id: null,
      frame_index: 10,
      tags: ["wrong_way"],
      updated_at: "2026-01-01T00:00:00+00:00"
    }),
    {
      caseId: "badcase_a",
      runId: "run_a",
      caseType: "误报 false_positive",
      module: "事件引擎 event_engine",
      statusLabel: "未处理 open",
      event: "-",
      track: "-",
      frame: "10",
      tags: "wrong_way",
      source: "manual",
      linkedFailedCaseId: "failed_eval_1",
      updatedAt: "2026-01-01T00:00:00+00:00"
    }
  );
});
