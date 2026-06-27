import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { copyFileSync, existsSync, mkdirSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const outDir = path.join(tmpdir(), `smarttraffic-overlay-components-${process.pid}`);

rmSync(outDir, { force: true, recursive: true });
mkdirSync(outDir, { recursive: true });
writeFileSync(path.join(outDir, "package.json"), "{\"type\":\"module\"}\n");
const nodeModulesLink = path.join(outDir, "node_modules");
if (!existsSync(nodeModulesLink)) {
  symlinkSync(path.join(repoRoot, "frontend/node_modules"), nodeModulesLink, "dir");
}

execFileSync(
  path.join(repoRoot, "frontend/node_modules/.bin/tsc"),
  [
    path.join(repoRoot, "frontend/src/components/DetectionOverlay.tsx"),
    path.join(repoRoot, "frontend/src/components/TrackOverlay.tsx"),
    "--rootDir",
    path.join(repoRoot, "frontend/src"),
    "--outDir",
    outDir,
    "--jsx",
    "react-jsx",
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

copyFileSync(
  path.join(outDir, "utils/videoOverlay.js"),
  path.join(outDir, "utils/videoOverlay")
);

const DetectionOverlay = (
  await import(pathToFileURL(path.join(outDir, "components/DetectionOverlay.js")).href)
).default;
const TrackOverlay = (
  await import(pathToFileURL(path.join(outDir, "components/TrackOverlay.js")).href)
).default;

test("DetectionOverlay accepts DB-backed object bbox without throwing", () => {
  assert.doesNotThrow(() =>
    DetectionOverlay({
      currentTimeMs: 0,
      frames: [
        {
          frame_index: 0,
          timestamp_ms: 0,
          detections: [
            {
              class_name: "car",
              confidence: "0.81",
              bbox: { x1: 1, y1: 2, x2: 30, y2: 40 }
            }
          ]
        }
      ]
    })
  );
});

test("TrackOverlay accepts DB-backed metadata bbox without throwing", () => {
  assert.doesNotThrow(() =>
    TrackOverlay({
      currentTimeMs: 0,
      frames: [
        {
          frame_index: 0,
          timestamp_ms: 0,
          tracks: [
            {
              track_id: "7",
              class_name: "car",
              confidence: "0.72",
              metadata: { x1: "1", y1: "2", x2: "30", y2: "40" }
            }
          ]
        }
      ],
      trajectoryFrames: []
    })
  );
});
