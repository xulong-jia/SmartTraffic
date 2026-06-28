import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const outDir = path.join(tmpdir(), `smarttraffic-review-metrics-${process.pid}`);

rmSync(outDir, { force: true, recursive: true });
mkdirSync(outDir, { recursive: true });
writeFileSync(path.join(outDir, "package.json"), "{\"type\":\"module\"}\n");

execFileSync(
  path.join(repoRoot, "frontend/node_modules/.bin/tsc"),
  [
    path.join(repoRoot, "frontend/src/utils/reviewMetrics.ts"),
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

const reviewMetrics = await import(pathToFileURL(path.join(outDir, "utils/reviewMetrics.js")).href);

test("buildReviewStatusCounts counts known statuses and unknown fallback", () => {
  const counts = reviewMetrics.buildReviewStatusCounts([
    { event_id: "event-a", run_id: "run-a", review_status: "pending" },
    { event_id: "event-b", run_id: "run-a", review_status: "confirmed" },
    { event_id: "event-c", run_id: "run-a", review_status: "false_positive" },
    { event_id: "event-d", run_id: "run-a", review_status: "ignored" },
    { event_id: "event-e", run_id: "run-a", review_status: "resolved" },
    { event_id: "event-f", run_id: "run-a", review_status: "unexpected" }
  ]);

  assert.deepEqual(counts, {
    pending: 1,
    confirmed: 1,
    false_positive: 1,
    false_negative: 0,
    ignored: 1,
    resolved: 1,
    unknown: 1
  });
});

test("formatReviewStatusLabel keeps compact labels for UI chips", () => {
  assert.equal(reviewMetrics.formatReviewStatusLabel("pending"), "待复核");
  assert.equal(reviewMetrics.formatReviewStatusLabel("false_positive"), "误报");
  assert.equal(reviewMetrics.formatReviewStatusLabel("false_negative"), "漏报");
  assert.equal(reviewMetrics.formatReviewStatusLabel("unexpected_status"), "unexpected_status");
});

test("buildReviewEventDisplaySummary normalizes optional fields", () => {
  const summary = reviewMetrics.buildReviewEventDisplaySummary({
    event_id: "event-a",
    run_id: "run-a",
    event_type: "danger_zone_intrusion",
    review_status: "pending",
    original_status: "pending",
    track_id: null,
    zone_id: "",
    start_frame: 10,
    end_frame: null,
    linked_alert_ids: ["alert-a", "alert-b"],
    comment_count: 0
  });

  assert.deepEqual(summary, {
    eventId: "event-a",
    runId: "run-a",
    eventType: "danger_zone_intrusion",
    statusLabel: "待复核",
    originalStatus: "pending",
    track: "-",
    zone: "-",
    frameRange: "10 -",
    linkedAlertCount: "2",
    commentCount: "0"
  });
});
