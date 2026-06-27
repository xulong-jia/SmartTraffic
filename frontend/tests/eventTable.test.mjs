import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const outDir = path.join(tmpdir(), `smarttraffic-event-table-${process.pid}`);

rmSync(outDir, { force: true, recursive: true });
mkdirSync(outDir, { recursive: true });
writeFileSync(path.join(outDir, "package.json"), "{\"type\":\"module\"}\n");

execFileSync(
  path.join(repoRoot, "frontend/node_modules/.bin/tsc"),
  [
    path.join(repoRoot, "frontend/src/utils/eventTable.ts"),
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

const eventTable = await import(pathToFileURL(path.join(outDir, "utils/eventTable.js")).href);

const events = [
  {
    event_id: "event-late",
    run_id: "run-1",
    event_type: "wrong_way_driving",
    severity: "warning",
    status: "pending",
    track_id: 9,
    zone_id: "zone-b",
    start_time_ms: 2000
  },
  {
    event_id: "event-early",
    run_id: "run-1",
    event_type: "danger_zone_intrusion",
    severity: "critical",
    status: "confirmed",
    track_id: null,
    zone_id: null,
    start_time_ms: 1000
  }
];

test("event table sorts by start time then event id", () => {
  assert.deepEqual(
    eventTable.sortEventTableRows(events).map((event) => event.event_id),
    ["event-early", "event-late"]
  );
});

test("event table filters by status event type and severity", () => {
  assert.deepEqual(
    eventTable
      .filterEventTableRows(events, {
        status: "pending",
        eventType: "wrong_way_driving",
        severity: "warning"
      })
      .map((event) => event.event_id),
    ["event-late"]
  );
  assert.deepEqual(eventTable.filterEventTableRows(events, { severity: "info" }), []);
});

test("event table rows normalize nullable fields and selection", () => {
  assert.deepEqual(eventTable.buildEventTableRows(events, "event-early"), [
    {
      id: "event-early",
      eventType: "danger_zone_intrusion",
      severity: "critical",
      status: "已确认 confirmed",
      trackId: "-",
      zoneId: "-",
      startTimeMs: "1000",
      runId: "run-1",
      selected: true
    },
    {
      id: "event-late",
      eventType: "wrong_way_driving",
      severity: "warning",
      status: "待处理 pending",
      trackId: "9",
      zoneId: "zone-b",
      startTimeMs: "2000",
      runId: "run-1",
      selected: false
    }
  ]);
});

test("event table empty labels expose loading error and empty states", () => {
  assert.equal(eventTable.eventTableEmptyLabel(true, "", []), "正在加载事件...");
  assert.equal(eventTable.eventTableEmptyLabel(false, "Request failed", []), "Request failed");
  assert.equal(eventTable.eventTableEmptyLabel(false, "", []), "暂无事件。请先运行一次视频分析。");
  assert.equal(eventTable.eventTableEmptyLabel(false, "", events), "");
});
