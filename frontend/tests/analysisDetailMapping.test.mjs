import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const outDir = path.join(tmpdir(), `smarttraffic-analysis-detail-mapping-${process.pid}`);

rmSync(outDir, { force: true, recursive: true });
mkdirSync(outDir, { recursive: true });
writeFileSync(path.join(outDir, "package.json"), "{\"type\":\"module\"}\n");

execFileSync(
  path.join(repoRoot, "frontend/node_modules/.bin/tsc"),
  [
    path.join(repoRoot, "frontend/src/utils/eventTimeline.ts"),
    path.join(repoRoot, "frontend/src/utils/videoOverlay.ts"),
    path.join(repoRoot, "frontend/src/utils/analysisDetailMapping.ts"),
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

const compiledPath = path.join(outDir, "utils/analysisDetailMapping.js");
writeFileSync(
  compiledPath,
  readFileSync(compiledPath, "utf8")
    .replace("\"./eventTimeline\"", "\"./eventTimeline.js\"")
    .replace("\"./videoOverlay\"", "\"./videoOverlay.js\"")
);

const mapping = await import(pathToFileURL(compiledPath).href);

test("buildOverlayDataBundle maps API responses into overlay props", () => {
  const bundle = mapping.buildOverlayDataBundle({
    detections: {
      run_id: "run_1",
      video_id: "video_1",
      summary: {},
      frames: [{ frame_index: 1, timestamp_ms: 33, detections: [] }],
      rows: [],
      limit: 50
    },
    tracks: {
      run_id: "run_1",
      video_id: "video_1",
      summary: {},
      frames: [{ frame_index: 1, timestamp_ms: 33, tracks: [] }],
      rows: [],
      limit: 50
    },
    trajectory: {
      run_id: "run_1",
      summary: {},
      frames: [{ frame_index: 1, timestamp_ms: 33, trajectory_points: [] }],
      rows: [],
      limit: 100
    },
    events: {
      run_id: "run_1",
      summary: {},
      events: [{ event_id: "event_1", track_id: 42, zone_id: "zone_1" }],
      event_evidence: [],
      rule_executions: [],
      limit: 100
    },
    zones: [{ id: "zone_1", name: "Lane", zone_type: "vehicle_lane", polygon: [[1, 1], [2, 1], [2, 2]], enabled: true, version: 1 }],
    selectedEventId: "event_1"
  });

  assert.equal(bundle.detections.length, 1);
  assert.equal(bundle.tracks.length, 1);
  assert.equal(bundle.trajectoryFrames.length, 1);
  assert.equal(bundle.events.length, 1);
  assert.equal(bundle.zones.length, 1);
  assert.equal(bundle.selectedTrackId, 42);
  assert.equal(bundle.selectedZoneId, "zone_1");
});

test("findSelectedEvent returns null when selection is missing", () => {
  assert.equal(mapping.findSelectedEvent([{ event_id: "event_1" }], "missing"), null);
  assert.deepEqual(mapping.findSelectedEvent([{ event_id: "event_1" }], "event_1"), {
    event_id: "event_1"
  });
});

test("inferOverlaySize uses boxes and zone coordinates with sane default", () => {
  assert.deepEqual(mapping.inferOverlaySize({}), { width: 960, height: 540 });
  assert.deepEqual(
    mapping.inferOverlaySize({
      detections: {
        run_id: "run_1",
        video_id: "video_1",
        summary: {},
        frames: [{ frame_index: 1, detections: [{ class_name: "car", confidence: 0.9, bbox: [0, 0, 1200, 700] }] }],
        rows: [],
        limit: 50
      }
    }),
    { width: 1200, height: 700 }
  );
});
