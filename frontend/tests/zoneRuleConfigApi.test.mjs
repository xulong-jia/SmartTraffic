import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const outDir = path.join(tmpdir(), `smarttraffic-zone-rule-config-api-${process.pid}`);

rmSync(outDir, { force: true, recursive: true });
mkdirSync(outDir, { recursive: true });
writeFileSync(path.join(outDir, "package.json"), "{\"type\":\"module\"}\n");

execFileSync(
  path.join(repoRoot, "frontend/node_modules/.bin/tsc"),
  [
    path.join(repoRoot, "frontend/src/utils/zoneRuleConfigApi.ts"),
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

const configApi = await import(pathToFileURL(path.join(outDir, "utils/zoneRuleConfigApi.js")).href);

test("parseTargetClasses builds stable API target class arrays", () => {
  assert.deepEqual(configApi.parseTargetClasses(" car, bus,,truck "), ["car", "bus", "truck"]);
});

test("buildEventRulePayload maps UI fields to backend event_rules shape", () => {
  const result = configApi.buildEventRulePayload({
    ...configApi.createEmptyEventRuleFormState(),
    name: "Wrong way",
    eventType: "wrong_way_driving",
    zoneId: "zone_lane_1",
    targetClassesText: "car,bus",
    parametersText: "{\"allowed_angle\":0}",
    cooldownSeconds: 3,
    severity: "high",
    version: 2,
    minTrackLength: 4
  });

  assert.deepEqual(result.errors, []);
  assert.deepEqual(result.payload, {
    name: "Wrong way",
    event_type: "wrong_way_driving",
    enabled: true,
    zone_id: "zone_lane_1",
    target_classes: ["car", "bus"],
    parameters: { allowed_angle: 0 },
    cooldown_seconds: 3,
    severity: "high",
    version: 2,
    min_track_length: 4
  });
});

test("buildEventRulePatchPayload preserves editable shape for existing rules", () => {
  const state = configApi.eventRuleToFormState({
    id: "rule_1",
    name: "Counter",
    event_type: "flow_counting",
    enabled: false,
    zone_id: "counting_zone",
    target_classes: ["car"],
    parameters: { direction: "positive" },
    cooldown_seconds: 1.5,
    severity: "medium",
    version: 5,
    min_track_length: 2
  });

  const result = configApi.buildEventRulePatchPayload(state);
  assert.deepEqual(result.errors, []);
  assert.equal(result.payload.enabled, false);
  assert.equal(result.payload.event_type, "flow_counting");
  assert.deepEqual(result.payload.parameters, { direction: "positive" });
});

test("invalid event rule form returns validation errors instead of payload", () => {
  const result = configApi.buildEventRulePayload({
    ...configApi.createEmptyEventRuleFormState(),
    name: "",
    eventType: "unsupported",
    parametersText: "[]",
    cooldownSeconds: -1
  });

  assert.equal(result.payload, null);
  assert.ok(result.errors.includes("Rule name is required."));
  assert.ok(result.errors.includes("Event type is unsupported."));
  assert.ok(result.errors.includes("Cooldown seconds must be non-negative."));
  assert.ok(result.errors.includes("Parameters JSON must be an object."));
});
