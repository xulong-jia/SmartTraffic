import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const outDir = path.join(tmpdir(), `smarttraffic-evaluation-metrics-${process.pid}`);

rmSync(outDir, { force: true, recursive: true });
mkdirSync(outDir, { recursive: true });
writeFileSync(path.join(outDir, "package.json"), "{\"type\":\"module\"}\n");

execFileSync(
  path.join(repoRoot, "frontend/node_modules/.bin/tsc"),
  [
    path.join(repoRoot, "frontend/src/utils/evaluationMetrics.ts"),
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

const evaluationMetrics = await import(
  pathToFileURL(path.join(outDir, "utils/evaluationMetrics.js")).href
);

const results = [
  {
    evaluation_result_id: "result_1",
    evaluation_run_id: "eval_1",
    run_id: "run_1",
    dataset_id: "dataset_1",
    evaluation_type: "event",
    metric_name: "event_precision",
    metric_value: 0.5,
    details: { status: "available" },
    created_at: "2026-01-01T00:00:00+00:00"
  },
  {
    evaluation_result_id: "result_2",
    evaluation_run_id: "eval_1",
    run_id: "run_1",
    dataset_id: "dataset_1",
    evaluation_type: "detection",
    metric_name: "detection_status",
    metric_value: null,
    details: { status: "not_applicable", reason: "missing detection annotations" },
    created_at: "2026-01-01T00:00:01+00:00"
  },
  {
    evaluation_result_id: "result_3",
    evaluation_run_id: "eval_1",
    run_id: "run_1",
    dataset_id: "dataset_1",
    evaluation_type: "regression",
    metric_name: "bad_case_regression_status",
    metric_value: null,
    details: { status: "planned" },
    created_at: "2026-01-01T00:00:02+00:00"
  },
  {
    evaluation_result_id: "result_4",
    evaluation_run_id: "eval_1",
    run_id: "run_1",
    dataset_id: "dataset_1",
    evaluation_type: "tracking",
    metric_name: "tracking_status",
    metric_value: null,
    details: {},
    created_at: "2026-01-01T00:00:03+00:00"
  }
];

test("buildEvaluationStatusCounts counts available, planned, not applicable, and unknown", () => {
  assert.deepEqual(evaluationMetrics.buildEvaluationStatusCounts(results), {
    available: 1,
    empty: 0,
    insufficient_data: 0,
    not_applicable: 1,
    planned: 1,
    unknown: 1
  });
});

test("formatEvaluationStatusLabel returns compact labels", () => {
  assert.equal(evaluationMetrics.formatEvaluationStatusLabel("not_applicable"), "Not applicable");
  assert.equal(evaluationMetrics.formatEvaluationStatusLabel("planned"), "Planned");
  assert.equal(evaluationMetrics.formatEvaluationStatusLabel("unexpected_status"), "Unexpected status");
});

test("normalizeMetricValue formats nulls and numeric values", () => {
  assert.equal(evaluationMetrics.normalizeMetricValue(null), "-");
  assert.equal(evaluationMetrics.normalizeMetricValue(0.333333), "0.333");
  assert.equal(evaluationMetrics.normalizeMetricValue(2), "2");
});

test("buildEvaluationResultDisplaySummary normalizes table values", () => {
  assert.deepEqual(evaluationMetrics.buildEvaluationResultDisplaySummary(results[1]), {
    evaluationRunId: "eval_1",
    runId: "run_1",
    datasetId: "dataset_1",
    evaluationType: "Detection",
    metricName: "Detection status",
    metricValue: "-",
    statusLabel: "Not applicable",
    reason: "missing detection annotations",
    createdAt: "2026-01-01T00:00:01+00:00"
  });
});

test("buildBadCaseRegressionDisplaySummary normalizes regression summary values", () => {
  assert.deepEqual(
    evaluationMetrics.buildBadCaseRegressionDisplaySummary({
      status: "available",
      total_cases: 4,
      open_cases: 1,
      fixed_cases: 2,
      verified_cases: 1,
      ignored_cases: 0,
      fixed_case_count: 2,
      reopened_case_count: 0,
      regression_pass_rate: 0.333333,
      definition: "verified_cases / max(fixed_cases + verified_cases + open_cases, 1)"
    }),
    {
      statusLabel: "Available",
      totalCases: "4",
      openCases: "1",
      fixedCases: "2",
      verifiedCases: "1",
      ignoredCases: "0",
      fixedCaseCount: "2",
      reopenedCaseCount: "0",
      regressionPassRate: "0.333",
      definition: "verified_cases / max(fixed_cases + verified_cases + open_cases, 1)"
    }
  );
});
