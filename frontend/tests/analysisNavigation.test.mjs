import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const outDir = path.join(tmpdir(), `smarttraffic-analysis-navigation-${process.pid}`);

rmSync(outDir, { force: true, recursive: true });
mkdirSync(outDir, { recursive: true });
writeFileSync(path.join(outDir, "package.json"), "{\"type\":\"module\"}\n");

execFileSync(
  path.join(repoRoot, "frontend/node_modules/.bin/tsc"),
  [
    path.join(repoRoot, "frontend/src/utils/analysisNavigation.ts"),
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

const navigation = await import(
  pathToFileURL(path.join(outDir, "analysisNavigation.js")).href
);

test("parseAnalysisRunIdFromSearch reads direct analysis links", () => {
  assert.equal(
    navigation.parseAnalysisRunIdFromSearch("?run_id=run_18101114a5e2"),
    "run_18101114a5e2"
  );
  assert.equal(navigation.parseAnalysisRunIdFromSearch("?run_id="), "");
});

test("resolveAnalysisInitialRunId prefers query run id over selected run", () => {
  assert.equal(
    navigation.resolveAnalysisInitialRunId("run_default", "?run_id=run_query"),
    "run_query"
  );
  assert.equal(navigation.resolveAnalysisInitialRunId("run_default", ""), "run_default");
});
