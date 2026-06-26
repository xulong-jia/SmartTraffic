import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const outDir = path.join(tmpdir(), `smarttraffic-zone-editor-state-${process.pid}`);

rmSync(outDir, { force: true, recursive: true });
mkdirSync(path.join(outDir, "utils"), { recursive: true });
writeFileSync(path.join(outDir, "package.json"), "{\"type\":\"module\"}\n");

execFileSync(
  path.join(repoRoot, "frontend/node_modules/.bin/tsc"),
  [
    path.join(repoRoot, "frontend/src/utils/zoneEditorGeometry.ts"),
    path.join(repoRoot, "frontend/src/utils/zoneEditorState.ts"),
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

const compiledStatePath = path.join(outDir, "utils/zoneEditorState.js");
writeFileSync(
  compiledStatePath,
  readFileSync(compiledStatePath, "utf8").replace(
    "\"./zoneEditorGeometry\"",
    "\"./zoneEditorGeometry.js\""
  )
);

const state = await import(pathToFileURL(path.join(outDir, "utils/zoneEditorState.js")).href);

test("validateZoneEditorState rejects missing name and short polygon", () => {
  const editor = state.createEmptyZoneEditorState();
  const result = state.validateZoneEditorState(editor);

  assert.equal(result.valid, false);
  assert.ok(result.errors.includes("Zone name is required."));
  assert.ok(result.errors.includes("Polygon requires at least three points."));
});

test("buildZonePayload maps polygon direction_json and counting_line_json", () => {
  const editor = {
    ...state.createEmptyZoneEditorState(),
    name: "Main lane",
    zoneType: "vehicle_lane",
    polygon: [
      { x: 10, y: 20 },
      { x: 120, y: 20 },
      { x: 120, y: 80 }
    ],
    directionLine: {
      start: { x: 10, y: 50 },
      end: { x: 120, y: 50 }
    },
    allowedAngle: 0,
    reverseAngleThreshold: 150,
    countingLine: {
      start: { x: 60, y: 20 },
      end: { x: 60, y: 80 }
    },
    inDirection: "positive",
    version: 2
  };

  assert.equal(state.validateZoneEditorState(editor, "direction").valid, true);

  assert.deepEqual(state.buildZonePayload(editor), {
    name: "Main lane",
    zone_type: "vehicle_lane",
    polygon: [
      [10, 20],
      [120, 20],
      [120, 80]
    ],
    direction: {
      start_point: [10, 50],
      end_point: [120, 50],
      allowed_angle: 0,
      reverse_angle_threshold: 150
    },
    counting_line: {
      start_point: [60, 20],
      end_point: [60, 80],
      in_direction: "positive",
      enabled: true
    },
    enabled: true,
    video_id: null,
    camera_id: null,
    version: 2
  });
});

test("zoneToEditorState hydrates existing API zones for PATCH editing", () => {
  const editor = state.zoneToEditorState({
    id: "zone_1",
    name: "Counter",
    zone_type: "counting_zone",
    polygon: [
      [1, 1],
      [5, 1],
      [5, 5]
    ],
    direction: null,
    counting_line: {
      start_point: [2, 1],
      end_point: [2, 5],
      in_direction: "negative",
      enabled: true
    },
    enabled: false,
    video_id: "video_1",
    camera_id: null,
    version: 3
  });

  assert.equal(editor.id, "zone_1");
  assert.equal(editor.zoneType, "counting_zone");
  assert.deepEqual(editor.countingLine.start, { x: 2, y: 1 });
  assert.equal(editor.inDirection, "negative");

  const patch = state.buildZonePatchPayload(editor);
  assert.equal(patch.enabled, false);
  assert.equal(patch.version, 3);
  assert.deepEqual(patch.counting_line?.start_point, [2, 1]);
});

test("line mode validation requires complete line when a line is being saved", () => {
  const editor = {
    ...state.createEmptyZoneEditorState(),
    name: "Wrong way lane",
    polygon: [
      { x: 0, y: 0 },
      { x: 10, y: 0 },
      { x: 10, y: 10 }
    ],
    directionLine: { start: { x: 1, y: 1 }, end: null }
  };

  const result = state.validateZoneEditorState(editor, "direction");
  assert.equal(result.valid, false);
  assert.ok(result.errors.includes("Direction line requires two points."));
});
