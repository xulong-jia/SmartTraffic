import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const outDir = path.join(tmpdir(), `smarttraffic-alert-panel-${process.pid}`);

rmSync(outDir, { force: true, recursive: true });
mkdirSync(outDir, { recursive: true });
writeFileSync(path.join(outDir, "package.json"), "{\"type\":\"module\"}\n");

execFileSync(
  path.join(repoRoot, "frontend/node_modules/.bin/tsc"),
  [
    path.join(repoRoot, "frontend/src/utils/alertPanel.ts"),
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

const alertPanel = await import(pathToFileURL(path.join(outDir, "utils/alertPanel.js")).href);

const alerts = [
  {
    id: "alert-critical",
    alert_id: "alert-critical",
    event_id: "event-1",
    video_id: "video-1",
    run_id: "run-1",
    alert_type: "danger_zone_intrusion",
    title: "Danger zone",
    message: "Vehicle entered danger zone",
    level: "critical",
    status: "new",
    track_id: 42,
    created_at: "2026-01-01T00:00:00+00:00"
  },
  {
    id: "alert-info",
    alert_id: "alert-info",
    event_id: "event-2",
    video_id: "video-1",
    run_id: "run-2",
    alert_type: "flow_counting",
    title: "",
    message: "Count update",
    level: "info",
    status: "resolved",
    track_id: null,
    created_at: "2026-01-01T00:01:00+00:00"
  }
];

test("alert panel filters by status and level", () => {
  assert.deepEqual(
    alertPanel.filterAlertPanelRows(alerts, { status: "new", level: "critical" }).map(
      (alert) => alert.id
    ),
    ["alert-critical"]
  );
  assert.deepEqual(alertPanel.filterAlertPanelRows(alerts, { status: "ignored" }), []);
});

test("alert panel rows are display ready and preserve selection", () => {
  assert.deepEqual(alertPanel.buildAlertPanelRows(alerts, "alert-critical"), [
    {
      id: "alert-critical",
      title: "Danger zone",
      message: "Vehicle entered danger zone",
      level: "严重",
      status: "新告警",
      eventId: "event-1",
      runId: "run-1",
      trackId: "42",
      createdAt: "2026-01-01T00:00:00+00:00",
      selected: true,
      canAcknowledge: true,
      canResolve: true,
      canIgnore: true
    },
    {
      id: "alert-info",
      title: "flow_counting",
      message: "Count update",
      level: "信息",
      status: "已解决",
      eventId: "event-2",
      runId: "run-2",
      trackId: "-",
      createdAt: "2026-01-01T00:01:00+00:00",
      selected: false,
      canAcknowledge: true,
      canResolve: false,
      canIgnore: true
    }
  ]);
});

test("alert action payload and empty labels are stable", () => {
  assert.deepEqual(alertPanel.buildAlertActionPayload("alert-1", "acknowledge"), {
    alertId: "alert-1",
    action: "acknowledge"
  });
  assert.equal(alertPanel.alertPanelEmptyLabel(false, "", []), "暂无告警。事件触发后会在这里显示。");
  assert.equal(alertPanel.alertPanelEmptyLabel(true, "", []), "正在加载告警...");
  assert.equal(alertPanel.alertPanelEmptyLabel(false, "Request failed", []), "Request failed");
  assert.equal(alertPanel.alertPanelEmptyLabel(false, "", alerts), "");
});
