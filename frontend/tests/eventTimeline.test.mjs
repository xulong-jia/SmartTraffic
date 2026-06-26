import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const outDir = path.join(tmpdir(), `smarttraffic-event-timeline-${process.pid}`);

rmSync(outDir, { force: true, recursive: true });
mkdirSync(outDir, { recursive: true });
writeFileSync(path.join(outDir, "package.json"), "{\"type\":\"module\"}\n");

execFileSync(
  path.join(repoRoot, "frontend/node_modules/.bin/tsc"),
  [
    path.join(repoRoot, "frontend/src/utils/eventTimeline.ts"),
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

const timeline = await import(pathToFileURL(path.join(outDir, "utils/eventTimeline.js")).href);

const events = [
  {
    event_id: "event_late",
    event_type: "illegal_parking",
    severity: "high",
    status: "new",
    start_time_ms: 2000,
    track_id: 2
  },
  {
    event_id: "event_early",
    event_type: "wrong_way_driving",
    severity: "medium",
    status: "confirmed",
    start_time_ms: 500,
    track_id: 1
  },
  {
    event_id: "event_frame",
    event_type: "wrong_way_driving",
    severity: "medium",
    status: "new",
    start_frame: 60,
    track_id: 3
  }
];

test("sortEventsByTime orders events by seek time", () => {
  assert.deepEqual(timeline.sortEventsByTime(events).map((event) => event.event_id), [
    "event_early",
    "event_late",
    "event_frame"
  ]);
});

test("filterEvents applies event_type severity and status filters", () => {
  const filtered = timeline.filterEvents(events, {
    eventType: "wrong_way_driving",
    severity: "medium",
    status: "new"
  });
  assert.deepEqual(filtered.map((event) => event.event_id), ["event_frame"]);
});

test("getEventSeekTimeMs falls back from timestamp to frame index", () => {
  assert.equal(timeline.getEventSeekTimeMs({ event_id: "a", timestamp_ms: 1200 }), 1200);
  assert.equal(Math.round(timeline.getEventSeekTimeMs({ event_id: "b", start_frame: 30 })), 1000);
  assert.equal(Math.round(timeline.getEventSeekTimeMs({ event_id: "c", frame_index: 15 })), 500);
});

test("selected and empty event helpers are stable", () => {
  assert.equal(timeline.getEventId({ event_id: "event_1" }, 4), "event_1");
  assert.equal(timeline.getEventId({}, 4), "event_4");
  assert.equal(timeline.isSelectedEvent({ event_id: "event_1" }, "event_1"), true);
  assert.deepEqual(timeline.filterEvents([], {}), []);
});

test("uniqueEventValues returns sorted filter options", () => {
  assert.deepEqual(timeline.uniqueEventValues(events, "event_type"), [
    "illegal_parking",
    "wrong_way_driving"
  ]);
});
