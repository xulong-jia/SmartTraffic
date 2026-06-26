import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const outDir = path.join(tmpdir(), `smarttraffic-zone-editor-geometry-${process.pid}`);

rmSync(outDir, { force: true, recursive: true });
mkdirSync(outDir, { recursive: true });
writeFileSync(path.join(outDir, "package.json"), "{\"type\":\"module\"}\n");

execFileSync(
  path.join(repoRoot, "frontend/node_modules/.bin/tsc"),
  [
    path.join(repoRoot, "frontend/src/utils/zoneEditorGeometry.ts"),
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

const geometry = await import(pathToFileURL(path.join(outDir, "zoneEditorGeometry.js")).href);

test("clampPoint keeps editor coordinates inside canvas bounds", () => {
  assert.deepEqual(geometry.clampPoint({ x: -4, y: 620 }, 960, 540), { x: 0, y: 540 });
  assert.deepEqual(geometry.clampPoint({ x: 480.1234, y: 120 }, 960, 540), {
    x: 480.1234,
    y: 120
  });
});

test("polygon and line validators enforce minimum geometry", () => {
  assert.equal(geometry.isValidPolygon([{ x: 0, y: 0 }, { x: 1, y: 1 }]), false);
  assert.equal(
    geometry.isValidPolygon([
      { x: 0, y: 0 },
      { x: 1, y: 1 },
      { x: 2, y: 0 }
    ]),
    true
  );
  assert.equal(geometry.isCompleteLine({ start: { x: 0, y: 0 }, end: null }), false);
  assert.equal(
    geometry.isCompleteLine({ start: { x: 0, y: 0 }, end: { x: 10, y: 0 } }),
    true
  );
});

test("lineAngleDegrees returns deterministic editor angle", () => {
  assert.equal(
    geometry.lineAngleDegrees({ start: { x: 0, y: 0 }, end: { x: 10, y: 0 } }),
    0
  );
  assert.equal(
    geometry.lineAngleDegrees({ start: { x: 0, y: 0 }, end: { x: 0, y: 10 } }),
    90
  );
  assert.equal(
    geometry.lineAngleDegrees({ start: { x: 0, y: 0 }, end: { x: 0, y: 0 } }),
    null
  );
});

test("API point conversion rounds and rejects malformed values", () => {
  assert.deepEqual(geometry.toApiPoint({ x: 1.23456, y: 7.0004 }), [1.235, 7]);
  assert.deepEqual(geometry.fromApiPoint([2, 3]), { x: 2, y: 3 });
  assert.equal(geometry.fromApiPoint([2]), null);
});
