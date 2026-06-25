import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const outDir = path.join(tmpdir(), `smarttraffic-review-navigation-${process.pid}`);

rmSync(outDir, { force: true, recursive: true });
mkdirSync(outDir, { recursive: true });
writeFileSync(path.join(outDir, "package.json"), "{\"type\":\"module\"}\n");

execFileSync(
  path.join(repoRoot, "frontend/node_modules/.bin/tsc"),
  [
    path.join(repoRoot, "frontend/src/utils/reviewNavigation.ts"),
    "--rootDir",
    path.join(repoRoot, "frontend/src"),
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

const navigation = await import(pathToFileURL(path.join(outDir, "utils/reviewNavigation.js")).href);

test("buildReviewLink includes run and event identifiers", () => {
  assert.equal(
    navigation.buildReviewLink("run_001", "event_123"),
    "/review?run_id=run_001&event_id=event_123"
  );
});

test("buildReviewLink includes alert context and optional filters", () => {
  assert.equal(
    navigation.buildReviewLink("run 001", "event/123", "alert?123", {
      status: "pending",
      event_type: "wrong_way_driving"
    }),
    "/review?run_id=run+001&event_id=event%2F123&alert_id=alert%3F123&status=pending&event_type=wrong_way_driving"
  );
});

test("buildReviewLink omits missing event and alert identifiers", () => {
  assert.equal(
    navigation.buildReviewLink("run_001", undefined, undefined, {
      status: "confirmed"
    }),
    "/review?run_id=run_001&status=confirmed"
  );
});

test("parseReviewQuery normalizes supported query parameters", () => {
  assert.deepEqual(
    navigation.parseReviewQuery(
      "?run_id=run_001&event_id=event_123&alert_id=alert_456&status=pending&event_type=illegal_parking&ignored=value"
    ),
    {
      run_id: "run_001",
      event_id: "event_123",
      alert_id: "alert_456",
      status: "pending",
      event_type: "illegal_parking"
    }
  );
});

test("normalizeReviewFiltersFromQuery preserves filter fields only", () => {
  assert.deepEqual(
    navigation.normalizeReviewFiltersFromQuery({
      run_id: "run_001",
      event_id: "event_123",
      alert_id: "alert_456",
      status: "resolved",
      event_type: "congestion"
    }),
    {
      runId: "run_001",
      status: "resolved",
      eventType: "congestion",
      eventId: "event_123",
      alertId: "alert_456"
    }
  );
});

test("parseReviewQuery tolerates empty and missing event context", () => {
  assert.deepEqual(navigation.parseReviewQuery(""), {});
  assert.deepEqual(navigation.parseReviewQuery("?status=pending&event_id="), {
    status: "pending"
  });
});
