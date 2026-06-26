import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const outDir = path.join(tmpdir(), `smarttraffic-review-workflow-${process.pid}`);

rmSync(outDir, { force: true, recursive: true });
mkdirSync(outDir, { recursive: true });
writeFileSync(path.join(outDir, "package.json"), "{\"type\":\"module\"}\n");

execFileSync(
  path.join(repoRoot, "frontend/node_modules/.bin/tsc"),
  [
    path.join(repoRoot, "frontend/src/utils/reviewWorkflow.ts"),
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

const reviewWorkflow = await import(
  pathToFileURL(path.join(outDir, "utils/reviewWorkflow.js")).href
);

const baseForm = {
  runId: " run_1 ",
  eventId: "event_1",
  reviewer: "",
  comment: " Needs follow-up ",
  alertId: "alert_1"
};

const detail = {
  run_id: "run_1",
  event: {
    event_id: "event_1",
    event_type: "wrong_way_driving",
    review_status: "false_positive",
    original_status: "pending"
  },
  review_state: null,
  linked_alerts: [],
  visual_artifacts: {},
  comments: [
    {
      review_id: "review_old",
      run_id: "run_1",
      event_id: "event_1",
      alert_id: null,
      action: "comment",
      after_status: "pending",
      comment: "old",
      reviewer: "a",
      created_at: "2026-01-01T00:00:00+00:00"
    },
    {
      review_id: "review_new",
      run_id: "run_1",
      event_id: "event_1",
      alert_id: null,
      action: "mark_false_positive",
      after_status: "false_positive",
      comment: "new",
      reviewer: "b",
      created_at: "2026-01-01T00:01:00+00:00"
    }
  ]
};

test("validateReviewWorkflowAction requires run, event, and comment for guarded actions", () => {
  assert.deepEqual(reviewWorkflow.validateReviewWorkflowAction("confirm", baseForm), {
    valid: true,
    message: ""
  });
  assert.deepEqual(
    reviewWorkflow.validateReviewWorkflowAction("rerun-rule", {
      ...baseForm,
      comment: ""
    }),
    {
      valid: false,
      message: "Comment is required for this action."
    }
  );
  assert.deepEqual(
    reviewWorkflow.validateReviewWorkflowAction("confirm", {
      ...baseForm,
      eventId: null
    }),
    {
      valid: false,
      message: "Select an event first."
    }
  );
});

test("buildReviewActionRequest normalizes reviewer, comment, and alert id", () => {
  assert.deepEqual(reviewWorkflow.buildReviewActionRequest(baseForm), {
    run_id: "run_1",
    comment: "Needs follow-up",
    reviewer: "local_reviewer",
    alert_id: "alert_1"
  });
});

test("buildBadCaseFromReviewRequest links the latest review and infers false positive case type", () => {
  assert.deepEqual(reviewWorkflow.buildBadCaseFromReviewRequest(detail, baseForm), {
    run_id: "run_1",
    event_id: "event_1",
    review_id: "review_new",
    case_type: "false_positive",
    module: "review_center",
    description: "Needs follow-up",
    expected_result: "Event rule should not emit this event.",
    actual_result: "wrong_way_driving was produced with original status pending.",
    root_cause: "Pending manual triage from Review Center.",
    tags: ["review_center", "needs_regression"]
  });
});

test("buildReviewSuccessMessage formats bad case and rerun responses", () => {
  assert.equal(
    reviewWorkflow.buildReviewSuccessMessage("bad-case", { case_id: "case_1" }),
    "Bad Case created: case_1."
  );
  assert.equal(
    reviewWorkflow.buildReviewSuccessMessage("rerun-rule", { task_id: "task_1" }),
    "Rule rerun requested: task_1."
  );
});
