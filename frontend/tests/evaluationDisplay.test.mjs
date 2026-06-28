import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const outDir = path.join(tmpdir(), `smarttraffic-evaluation-display-${process.pid}`);

rmSync(outDir, { force: true, recursive: true });
mkdirSync(outDir, { recursive: true });
writeFileSync(path.join(outDir, "package.json"), "{\"type\":\"module\"}\n");

execFileSync(
  path.join(repoRoot, "frontend/node_modules/.bin/tsc"),
  [
    path.join(repoRoot, "frontend/src/utils/evaluationDisplay.ts"),
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

const compiledDisplayPath = path.join(outDir, "utils/evaluationDisplay.js");
writeFileSync(
  compiledDisplayPath,
  readFileSync(compiledDisplayPath, "utf8").replace(
    'from "./evaluationMetrics";',
    'from "./evaluationMetrics.js";'
  )
);

const evaluationDisplay = await import(pathToFileURL(compiledDisplayPath).href);

const result = {
  evaluation_result_id: "result_1",
  evaluation_run_id: "eval_1",
  run_id: "run_1",
  dataset_id: "dataset_1",
  evaluation_type: "detection",
  metric_name: "detection_map",
  metric_value: 0.75,
  details: { status: "available", reason: "ok" },
  created_at: "2026-01-01T00:00:00+00:00"
};

const insufficientResult = {
  ...result,
  evaluation_result_id: "result_2",
  metric_value: null,
  details: { status: "insufficient_data", reason: "not_enough_annotations" }
};

const failedCase = {
  failed_case_id: "failed_1",
  evaluation_run_id: "eval_1",
  run_id: "run_1",
  dataset_id: "dataset_1",
  failure_type: "detection_miss",
  module: "detector",
  expected: { class_name: "car" },
  actual: { class_name: null },
  frame_range: { start_frame: 10, end_frame: 12 },
  suggested_bad_case_type: "detection_miss",
  created_at: "2026-01-01T00:00:00+00:00"
};

test("buildEvaluationMetricCards produces display cards from result rows", () => {
  assert.deepEqual(evaluationDisplay.buildEvaluationMetricCards([result]), [
    {
      key: "result_1",
      label: "检测 · Detection map",
      value: "0.750",
      status: "可用",
      detail: "ok"
    }
  ]);
});

test("buildInsufficientDataLabel makes missing data boundary explicit", () => {
  assert.equal(
    evaluationDisplay.buildInsufficientDataLabel(insufficientResult),
    "数据不足：缺少标注或数据，不计为 0 分。"
  );
});

test("buildFailedCaseRows normalizes failed case table values", () => {
  assert.deepEqual(evaluationDisplay.buildFailedCaseRows([failedCase]), [
    {
      failedCaseId: "failed_1",
      evaluationRunId: "eval_1",
      runId: "run_1",
      datasetId: "dataset_1",
      failureType: "Detection miss",
      module: "detector",
      frameRange: "10 12",
      suggestedBadCaseType: "detection_miss",
      expected: "{\"class_name\":\"car\"}",
      actual: "{\"class_name\":null}",
      createdAt: "2026-01-01T00:00:00+00:00"
    }
  ]);
});

test("buildFailedCaseBadCaseRequest creates conversion payload", () => {
  assert.deepEqual(evaluationDisplay.buildFailedCaseBadCaseRequest(failedCase), {
    run_id: "run_1",
    failed_case_id: "failed_1",
    case_type: "detection_miss",
    module: "detector",
    description: "detection_miss from evaluation eval_1",
    expected_result: "{\"class_name\":\"car\"}",
    actual_result: "{\"class_name\":null}",
    root_cause: "Pending triage from Evaluation Center.",
    tags: ["evaluation", "failed_case"]
  });
});

test("formatEvaluationBoundaryForType labels non-official metric boundaries", () => {
  assert.equal(
    evaluationDisplay.formatEvaluationBoundaryForType("tracking"),
    "轻量确定性帧级关联指标，不是 TrackEval official metrics。"
  );
});
