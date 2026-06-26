import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const outDir = path.join(tmpdir(), `smarttraffic-video-overlay-${process.pid}`);

rmSync(outDir, { force: true, recursive: true });
mkdirSync(outDir, { recursive: true });
writeFileSync(path.join(outDir, "package.json"), "{\"type\":\"module\"}\n");

execFileSync(
  path.join(repoRoot, "frontend/node_modules/.bin/tsc"),
  [
    path.join(repoRoot, "frontend/src/utils/videoOverlay.ts"),
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

const overlay = await import(pathToFileURL(path.join(outDir, "utils/videoOverlay.js")).href);

test("computeAspectFit and scaleBox preserve aspect ratio", () => {
  const fit = overlay.computeAspectFit(1920, 1080, 960, 540);
  assert.equal(fit.scale, 0.5);
  assert.deepEqual(overlay.scalePoint([100, 50], fit), { x: 50, y: 25 });
  assert.deepEqual(overlay.scaleBox([10, 20, 110, 220], fit), {
    x: 5,
    y: 10,
    width: 50,
    height: 100
  });
});

test("clampBox bounds bboxes inside source video size", () => {
  assert.deepEqual(overlay.clampBox([-10, 20, 1200, 700], 960, 540), [0, 20, 960, 540]);
});

test("filterDetectionsForTime and filterTracksForTime pick nearest frame", () => {
  const detections = overlay.filterDetectionsForTime(
    [
      { frame_index: 0, timestamp_ms: 0, detections: [{ class_name: "car", confidence: 0.9, bbox: [0, 0, 10, 10] }] },
      { frame_index: 10, timestamp_ms: 1000, detections: [{ class_name: "bus", confidence: 0.8, bbox: [1, 1, 11, 11] }] }
    ],
    850
  );
  assert.equal(detections[0].class_name, "bus");

  const tracks = overlay.filterTracksForTime(
    [
      { frame_index: 0, timestamp_ms: 0, tracks: [{ track_id: 1, class_name: "car", confidence: 0.9, bbox: [0, 0, 10, 10], center: [5, 5], state: "tracked" }] },
      { frame_index: 3, timestamp_ms: 300, tracks: [{ track_id: 2, class_name: "truck", confidence: 0.7, bbox: [2, 2, 12, 12], center: [7, 7], state: "tracked" }] }
    ],
    260
  );
  assert.equal(tracks[0].track_id, 2);
});

test("groupTrajectoryPolylines groups track points and highlights selected track", () => {
  const polylines = overlay.groupTrajectoryPolylines(
    [
      { frame_index: 0, timestamp_ms: 0, trajectory_points: [{ track_id: 4, center: [1, 1] }] },
      { frame_index: 1, timestamp_ms: 33, trajectory_points: [{ track_id: 4, center: [2, 2] }] },
      { frame_index: 2, timestamp_ms: 66, trajectory_points: [{ track_id: 5, center: [9, 9] }] }
    ],
    50,
    4
  );
  assert.equal(polylines.length, 2);
  assert.equal(polylines.find((item) => item.trackId === 4).highlighted, true);
  assert.deepEqual(polylines.find((item) => item.trackId === 4).points, [
    { x: 1, y: 1 },
    { x: 2, y: 2 }
  ]);
});

test("zone and selected event helpers map overlay highlights", () => {
  assert.deepEqual(
    overlay.zonePolygonPoints({
      id: "zone_1",
      name: "Lane",
      zone_type: "vehicle_lane",
      polygon: [[1, 2], [3, 4], [5, 6]],
      enabled: true,
      version: 1
    }),
    [{ x: 1, y: 2 }, { x: 3, y: 4 }, { x: 5, y: 6 }]
  );
  assert.equal(overlay.selectedTrackIdFromEvent({ event_id: "e1", track_id: 7 }), 7);
  assert.equal(overlay.selectedZoneIdFromEvent({ event_id: "e1", zone_id: "zone_1" }), "zone_1");
  assert.equal(overlay.isTrackHighlighted(7, 7), true);
  assert.equal(overlay.isZoneHighlighted("zone_1", "zone_1"), true);
});
