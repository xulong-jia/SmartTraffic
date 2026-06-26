import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const outDir = path.join(tmpdir(), `smarttraffic-realtime-preview-${process.pid}`);

rmSync(outDir, { force: true, recursive: true });
mkdirSync(outDir, { recursive: true });
writeFileSync(path.join(outDir, "package.json"), "{\"type\":\"module\"}\n");

execFileSync(
  path.join(repoRoot, "frontend/node_modules/.bin/tsc"),
  [
    path.join(repoRoot, "frontend/src/utils/realtimePreview.ts"),
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

const realtimePreview = await import(
  pathToFileURL(path.join(outDir, "utils/realtimePreview.js")).href
);

const camera = {
  id: "camera_1",
  name: "Gate camera",
  source_type: "rtsp",
  masked_stream_url: "rtsp://***@example.local/...",
  enabled: true,
  status: "active",
  created_at: "2026-01-01T00:00:00+00:00",
  updated_at: "2026-01-01T00:00:00+00:00"
};

test("camera source and masked display helpers are deterministic", () => {
  assert.equal(realtimePreview.formatCameraSourceLabel("rtsp"), "RTSP");
  assert.equal(realtimePreview.formatCameraSourceLabel("file"), "Local file");
  assert.equal(realtimePreview.buildMaskedStreamDisplay(camera), "rtsp://***@example.local/...");
  assert.equal(realtimePreview.buildMaskedStreamDisplay(null), "No camera selected");
});

test("start disabled reason reflects camera selection and enabled state", () => {
  assert.equal(realtimePreview.buildStartDisabledReason(null), "Select a camera");
  assert.equal(
    realtimePreview.buildStartDisabledReason({ ...camera, enabled: false }),
    "Camera disabled"
  );
  assert.equal(realtimePreview.buildStartDisabledReason(camera), "");
});

test("status cards expose realtime preview counts", () => {
  assert.deepEqual(
    realtimePreview.buildRealtimeStatusCards({
      camera_id: "camera_1",
      status: "running",
      task_id: "task_1",
      task_type: "realtime_process",
      video_id: "video_1",
      source_type: "mock",
      frame_count: 3,
      event_count: 1,
      alert_count: 1
    }),
    [
      { label: "Status", value: "running" },
      { label: "Frames", value: 3 },
      { label: "Events", value: 1 },
      { label: "Alerts", value: 1 }
    ]
  );
});

test("recent frame event and alert rows are display ready", () => {
  assert.deepEqual(
    realtimePreview.buildFrameRows([
      {
        id: "frame_1",
        camera_id: "camera_1",
        frame_index: 2,
        timestamp_ms: 2000,
        source_type: "mock",
        source_label: "Mock source",
        status: "mock_frame",
        description: "preview",
        created_at: "2026-01-01T00:00:00+00:00"
      }
    ]),
    [
      {
        id: "frame_1",
        frame: 2,
        source: "Mock source",
        status: "mock_frame",
        timestamp: 2000,
        description: "preview"
      }
    ]
  );
  assert.deepEqual(
    realtimePreview.buildEventRows([
      {
        id: "event_1",
        camera_id: "camera_1",
        event_type: "motion",
        severity: "low",
        status: "preview",
        frame_index: 2,
        description: "motion",
        created_at: "2026-01-01T00:00:00+00:00"
      }
    ]),
    [
      {
        id: "event_1",
        type: "motion",
        severity: "low",
        frame: 2,
        status: "preview",
        description: "motion"
      }
    ]
  );
  assert.deepEqual(
    realtimePreview.buildAlertRows([
      {
        id: "alert_1",
        camera_id: "camera_1",
        level: "info",
        status: "preview",
        event_type: "motion",
        message: "alert",
        created_at: "2026-01-01T00:00:00+00:00"
      }
    ]),
    [
      {
        id: "alert_1",
        level: "info",
        type: "motion",
        status: "preview",
        message: "alert"
      }
    ]
  );
});
