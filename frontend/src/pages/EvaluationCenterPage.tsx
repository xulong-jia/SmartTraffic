import { useEffect, useState } from "react";

import {
  getEvaluationSummary,
  listEvaluationDatasets,
  listEvaluationFailedCases,
  listEvaluationResults,
  listEvaluationRuns,
  registerEvaluationDataset,
  runEvaluation
} from "../api/evaluation";
import type {
  EvaluationDatasetListResponse,
  EvaluationFailedCaseListResponse,
  EvaluationResultListResponse,
  EvaluationRunListResponse,
  EvaluationSummaryArtifact,
  EvaluationType
} from "../types";
import {
  EVALUATION_TYPE_KEYS,
  buildEvaluationResultDisplaySummary,
  buildEvaluationStatusCounts,
  formatEvaluationStatusLabel,
  formatEvaluationTypeLabel,
  normalizeMetricValue
} from "../utils/evaluationMetrics";

interface DatasetFormState {
  dataset_id: string;
  name: string;
  dataset_type: EvaluationType | string;
  expected_events_path: string;
  expected_counts_path: string;
  annotation_path: string;
}

const emptyDatasetForm: DatasetFormState = {
  dataset_id: "",
  name: "",
  dataset_type: "event",
  expected_events_path: "",
  expected_counts_path: "",
  annotation_path: ""
};

export default function EvaluationCenterPage() {
  const [runId, setRunId] = useState("");
  const [datasetId, setDatasetId] = useState("");
  const [evaluationType, setEvaluationType] = useState<EvaluationType | string>("event");
  const [datasets, setDatasets] = useState<EvaluationDatasetListResponse | null>(null);
  const [runs, setRuns] = useState<EvaluationRunListResponse | null>(null);
  const [results, setResults] = useState<EvaluationResultListResponse | null>(null);
  const [failedCases, setFailedCases] = useState<EvaluationFailedCaseListResponse | null>(null);
  const [summary, setSummary] = useState<EvaluationSummaryArtifact | null>(null);
  const [datasetForm, setDatasetForm] = useState<DatasetFormState>(emptyDatasetForm);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState<"dataset" | "run" | null>(null);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const resultItems = results?.items ?? [];
  const statusCounts = buildEvaluationStatusCounts(resultItems);

  useEffect(() => {
    void loadEvaluationState();
  }, []);

  async function loadEvaluationState(targetRunId = runId) {
    setLoading(true);
    setError("");
    setSuccessMessage("");
    try {
      const normalizedRunId = normalizeOptional(targetRunId);
      const [datasetPayload, runPayload, resultPayload, failedCasePayload] =
        await Promise.all([
          listEvaluationDatasets(),
          listEvaluationRuns({ run_id: normalizedRunId, limit: 100, offset: 0 }),
          listEvaluationResults({
            run_id: normalizedRunId,
            evaluation_type: normalizeOptional(evaluationType),
            limit: 100,
            offset: 0
          }),
          listEvaluationFailedCases({ run_id: normalizedRunId, limit: 100, offset: 0 })
        ]);
      setDatasets(datasetPayload);
      setRuns(runPayload);
      setResults(resultPayload);
      setFailedCases(failedCasePayload);
      if (normalizedRunId) {
        setSummary(await getEvaluationSummary(normalizedRunId));
      } else {
        setSummary(null);
      }
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Evaluation request failed");
    } finally {
      setLoading(false);
    }
  }

  async function submitDataset() {
    if (!datasetForm.dataset_id.trim() || !datasetForm.name.trim()) {
      setError("dataset_id and name are required.");
      return;
    }
    setSubmitting("dataset");
    setError("");
    setSuccessMessage("");
    try {
      const created = await registerEvaluationDataset({
        dataset_id: datasetForm.dataset_id.trim(),
        name: datasetForm.name.trim(),
        dataset_type: datasetForm.dataset_type,
        expected_events_path: normalizeOptional(datasetForm.expected_events_path),
        expected_counts_path: normalizeOptional(datasetForm.expected_counts_path),
        annotation_path: normalizeOptional(datasetForm.annotation_path)
      });
      setDatasetId(created.dataset_id);
      setDatasetForm({ ...emptyDatasetForm, dataset_type: created.dataset_type });
      setSuccessMessage(`Registered ${created.dataset_id}.`);
      await loadEvaluationState();
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Dataset registration failed");
    } finally {
      setSubmitting(null);
    }
  }

  async function submitRun() {
    const normalizedRunId = runId.trim();
    if (!normalizedRunId) {
      setError("run_id is required.");
      return;
    }
    setSubmitting("run");
    setError("");
    setSuccessMessage("");
    try {
      const response = await runEvaluation({
        run_id: normalizedRunId,
        dataset_id: normalizeOptional(datasetId),
        evaluation_type: evaluationType
      });
      setSuccessMessage(`Completed ${response.evaluation_run.evaluation_run_id}.`);
      setSummary(response.summary);
      await loadEvaluationState(normalizedRunId);
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Evaluation run failed");
    } finally {
      setSubmitting(null);
    }
  }

  return (
    <>
      <header className="page-header">
        <div>
          <h2>Evaluation Center</h2>
          <p>Artifact-backed Stage 8EFG MVP</p>
        </div>
        <button type="button" onClick={() => loadEvaluationState()} disabled={loading}>
          Refresh
        </button>
      </header>

      <section className="panel">
        <div className="toolbar">
          <label>
            Run ID
            <input
              placeholder="run_..."
              value={runId}
              onChange={(event) => setRunId(event.target.value)}
            />
          </label>
          <label>
            Dataset
            <select value={datasetId} onChange={(event) => setDatasetId(event.target.value)}>
              <option value="">None</option>
              {(datasets?.datasets ?? []).map((dataset) => (
                <option key={dataset.dataset_id} value={dataset.dataset_id}>
                  {dataset.dataset_id}
                </option>
              ))}
            </select>
          </label>
          <label>
            Type
            <select
              value={evaluationType}
              onChange={(event) => setEvaluationType(event.target.value)}
            >
              {EVALUATION_TYPE_KEYS.map((value) => (
                <option key={value} value={value}>
                  {formatEvaluationTypeLabel(value)}
                </option>
              ))}
            </select>
          </label>
          <button type="button" onClick={submitRun} disabled={submitting === "run"}>
            Run
          </button>
          <button type="button" onClick={() => loadEvaluationState()} disabled={loading}>
            Apply
          </button>
        </div>
        {loading ? <p className="muted">Loading evaluations</p> : null}
        {error ? <p className="status-pill status-error">{error}</p> : null}
        {successMessage ? (
          <p className="status-pill status-available">{successMessage}</p>
        ) : null}
        <div className="metric-row">
          <MetricCard label="Results" value={String(results?.total ?? 0)} />
          <MetricCard label="Available" value={String(statusCounts.available)} />
          <MetricCard label="Planned" value={String(statusCounts.planned)} />
          <MetricCard label="Failed Cases" value={String(failedCases?.total ?? 0)} />
        </div>
      </section>

      <div className="grid two">
        <section className="panel">
          <div className="section-heading-row">
            <h3>Datasets</h3>
          </div>
          <div className="toolbar">
            <label>
              ID
              <input
                value={datasetForm.dataset_id}
                onChange={(event) =>
                  setDatasetForm({ ...datasetForm, dataset_id: event.target.value })
                }
              />
            </label>
            <label>
              Name
              <input
                value={datasetForm.name}
                onChange={(event) =>
                  setDatasetForm({ ...datasetForm, name: event.target.value })
                }
              />
            </label>
            <label>
              Type
              <select
                value={datasetForm.dataset_type}
                onChange={(event) =>
                  setDatasetForm({ ...datasetForm, dataset_type: event.target.value })
                }
              >
                {EVALUATION_TYPE_KEYS.map((value) => (
                  <option key={value} value={value}>
                    {formatEvaluationTypeLabel(value)}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="toolbar">
            <label>
              Expected Events
              <input
                placeholder="expected/events.json"
                value={datasetForm.expected_events_path}
                onChange={(event) =>
                  setDatasetForm({
                    ...datasetForm,
                    expected_events_path: event.target.value
                  })
                }
              />
            </label>
            <label>
              Expected Counts
              <input
                placeholder="expected/counts.json"
                value={datasetForm.expected_counts_path}
                onChange={(event) =>
                  setDatasetForm({
                    ...datasetForm,
                    expected_counts_path: event.target.value
                  })
                }
              />
            </label>
            <label>
              Annotation
              <input
                placeholder="annotations/dataset.json"
                value={datasetForm.annotation_path}
                onChange={(event) =>
                  setDatasetForm({ ...datasetForm, annotation_path: event.target.value })
                }
              />
            </label>
            <button
              type="button"
              onClick={submitDataset}
              disabled={submitting === "dataset"}
            >
              Register
            </button>
          </div>
          <DatasetTable data={datasets} />
        </section>

        <section className="panel">
          <div className="section-heading-row">
            <h3>Runs</h3>
          </div>
          <RunsTable data={runs} />
        </section>
      </div>

      <section className="panel">
        <div className="section-heading-row">
          <h3>Results</h3>
        </div>
        <ResultsTable data={results} />
      </section>

      <div className="grid two">
        <section className="panel">
          <div className="section-heading-row">
            <h3>Failed Cases</h3>
          </div>
          <FailedCasesTable data={failedCases} />
        </section>

        <section className="panel">
          <div className="section-heading-row">
            <h3>Summary</h3>
          </div>
          {summary ? (
            <pre>{JSON.stringify(summary.summary, null, 2)}</pre>
          ) : (
            <p className="muted">Select a run to load summary.</p>
          )}
        </section>
      </div>
    </>
  );
}

function DatasetTable({ data }: { data: EvaluationDatasetListResponse | null }) {
  const rows = data?.datasets ?? [];
  if (rows.length === 0) {
    return <p className="muted">No evaluation datasets.</p>;
  }
  return (
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Name</th>
          <th>Type</th>
          <th>Source</th>
          <th>Created</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((dataset) => (
          <tr key={dataset.dataset_id}>
            <td>{dataset.dataset_id}</td>
            <td>{dataset.name}</td>
            <td>{formatEvaluationTypeLabel(dataset.dataset_type)}</td>
            <td>{dataset.source}</td>
            <td>{dataset.created_at}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function RunsTable({ data }: { data: EvaluationRunListResponse | null }) {
  const rows = data?.items ?? [];
  if (rows.length === 0) {
    return <p className="muted">No evaluation runs.</p>;
  }
  return (
    <table>
      <thead>
        <tr>
          <th>Evaluation Run</th>
          <th>Run</th>
          <th>Dataset</th>
          <th>Type</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((run) => (
          <tr key={run.evaluation_run_id}>
            <td>{run.evaluation_run_id}</td>
            <td>{run.run_id}</td>
            <td>{run.dataset_id || "-"}</td>
            <td>{formatEvaluationTypeLabel(run.evaluation_type)}</td>
            <td>
              <span className={`status-pill status-${run.status}`}>{run.status}</span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ResultsTable({ data }: { data: EvaluationResultListResponse | null }) {
  const rows = data?.items ?? [];
  if (rows.length === 0) {
    return <p className="muted">No evaluation results.</p>;
  }
  return (
    <table>
      <thead>
        <tr>
          <th>Evaluation Run</th>
          <th>Run</th>
          <th>Dataset</th>
          <th>Type</th>
          <th>Metric</th>
          <th>Value</th>
          <th>Status</th>
          <th>Reason</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((result) => {
          const summary = buildEvaluationResultDisplaySummary(result);
          return (
            <tr key={result.evaluation_result_id}>
              <td>{summary.evaluationRunId}</td>
              <td>{summary.runId}</td>
              <td>{summary.datasetId}</td>
              <td>{summary.evaluationType}</td>
              <td>{summary.metricName}</td>
              <td>{summary.metricValue}</td>
              <td>
                <span className={`status-pill status-${statusClassName(summary.statusLabel)}`}>
                  {summary.statusLabel}
                </span>
              </td>
              <td>{summary.reason}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function FailedCasesTable({ data }: { data: EvaluationFailedCaseListResponse | null }) {
  const rows = data?.items ?? [];
  if (rows.length === 0) {
    return <p className="muted">No failed cases.</p>;
  }
  return (
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Run</th>
          <th>Type</th>
          <th>Module</th>
          <th>Suggested</th>
          <th>Created</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((failedCase) => (
          <tr key={failedCase.failed_case_id}>
            <td>{failedCase.failed_case_id}</td>
            <td>{failedCase.run_id}</td>
            <td>{failedCase.failure_type}</td>
            <td>{failedCase.module}</td>
            <td>{failedCase.suggested_bad_case_type || "-"}</td>
            <td>{failedCase.created_at}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-card">
      <span className="muted">{label}</span>
      <span className="metric-value">{normalizeMetricValue(value)}</span>
    </div>
  );
}

function normalizeOptional(value: string | null | undefined): string | undefined {
  const trimmed = value?.trim();
  return trimmed ? trimmed : undefined;
}

function statusClassName(value: string): string {
  return value.toLowerCase().split(" ").join("_");
}
