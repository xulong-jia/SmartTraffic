import { useEffect, useState } from "react";

import { createBadCaseFromFailedCase } from "../api/badCases";
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
  buildBadCaseRegressionDisplaySummary,
  buildEvaluationResultDisplaySummary,
  buildEvaluationStatusCounts,
  formatEvaluationTypeLabel,
  normalizeMetricValue
} from "../utils/evaluationMetrics";
import {
  EVALUATION_BOUNDARY_NOTICES,
  buildEvaluationMetricCards,
  buildEvaluationResultJson,
  buildFailedCaseBadCaseRequest,
  buildFailedCaseRows,
  buildInsufficientDataLabel,
  buildRegressionSummaryCards,
  formatEvaluationBoundaryForType
} from "../utils/evaluationDisplay";

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
  const [convertingFailedCaseId, setConvertingFailedCaseId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const resultItems = results?.items ?? [];
  const statusCounts = buildEvaluationStatusCounts(resultItems);
  const metricCards = buildEvaluationMetricCards(resultItems).slice(0, 6);
  const regressionCards = buildRegressionSummaryCards(summary);

  useEffect(() => {
    void loadEvaluationState();
  }, []);

  async function loadEvaluationState(targetRunId = runId) {
    setLoading(true);
    setError("");
    setSuccessMessage("");
    try {
      const normalizedRunId = normalizeOptional(targetRunId);
      const normalizedDatasetId = normalizeOptional(datasetId);
      const [datasetPayload, runPayload, resultPayload, failedCasePayload] =
        await Promise.all([
          listEvaluationDatasets(),
          listEvaluationRuns({
            run_id: normalizedRunId,
            dataset_id: normalizedDatasetId,
            evaluation_type: normalizeOptional(evaluationType),
            limit: 100,
            offset: 0
          }),
          listEvaluationResults({
            run_id: normalizedRunId,
            dataset_id: normalizedDatasetId,
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

  async function convertFailedCase(failedCaseId: string) {
    const failedCase = failedCases?.items.find((item) => item.failed_case_id === failedCaseId);
    if (!failedCase) {
      setError("Failed case is not loaded.");
      return;
    }
    setConvertingFailedCaseId(failedCaseId);
    setError("");
    setSuccessMessage("");
    try {
      const created = await createBadCaseFromFailedCase(
        buildFailedCaseBadCaseRequest(failedCase)
      );
      setSuccessMessage(`Created ${created.case_id} from ${failedCaseId}.`);
      await loadEvaluationState(failedCase.run_id);
    } catch (currentError) {
      setError(
        currentError instanceof Error ? currentError.message : "Failed case conversion failed"
      );
    } finally {
      setConvertingFailedCaseId(null);
    }
  }

  return (
    <>
      <header className="page-header">
        <div>
          <h2>评测中心 Evaluation Center</h2>
          <p>查看检测、跟踪、轨迹、事件和流量统计的本地评测结果。</p>
        </div>
        <button type="button" onClick={() => loadEvaluationState()} disabled={loading}>
          刷新 Refresh
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
            数据集 Dataset
            <select value={datasetId} onChange={(event) => setDatasetId(event.target.value)}>
              <option value="">无 None</option>
              {(datasets?.datasets ?? []).map((dataset) => (
                <option key={dataset.dataset_id} value={dataset.dataset_id}>
                  {dataset.dataset_id}
                </option>
              ))}
            </select>
          </label>
          <label>
            类型 Type
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
            运行评测 Run Evaluation
          </button>
          <button type="button" onClick={() => loadEvaluationState()} disabled={loading}>
            应用 Apply
          </button>
        </div>
        {loading ? <p className="muted">正在加载评测...</p> : null}
        {error ? <p className="alert-box error">{error}</p> : null}
        {successMessage ? (
          <p className="alert-box success">{successMessage}</p>
        ) : null}
        <div className="metric-row">
          <MetricCard label="结果 Results" value={String(results?.total ?? 0)} />
          <MetricCard label="可用 Available" value={String(statusCounts.available)} />
          <MetricCard label="数据不足 Insufficient" value={String(statusCounts.insufficient_data)} />
          <MetricCard label="失败用例 Failed Cases" value={String(failedCases?.total ?? 0)} />
        </div>
        <div className="info-callout">
          <h3>评测边界 Evaluation Boundaries</h3>
          <ul className="compact-list">
            {EVALUATION_BOUNDARY_NOTICES.map((notice) => (
              <li key={notice.key}>
                <strong>{notice.label}:</strong> {notice.detail}
              </li>
            ))}
          </ul>
          <p className="muted">{formatEvaluationBoundaryForType(String(evaluationType))}</p>
        </div>
        {metricCards.length > 0 ? (
          <div className="metric-row evaluation-card-grid">
            {metricCards.map((card) => (
              <MetricCard
                key={card.key}
                label={`${card.label} (${card.status})`}
                value={card.value}
              />
            ))}
          </div>
        ) : null}
      </section>

      <div className="grid two content-grid">
        <section className="panel">
          <div className="section-heading-row">
            <h3>数据集 Datasets</h3>
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
              名称 Name
              <input
                value={datasetForm.name}
                onChange={(event) =>
                  setDatasetForm({ ...datasetForm, name: event.target.value })
                }
              />
            </label>
            <label>
              类型 Type
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
              期望事件 Expected Events
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
              期望计数 Expected Counts
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
              注册 Register
            </button>
          </div>
          <DatasetTable data={datasets} />
        </section>

        <section className="panel">
          <div className="section-heading-row">
            <h3>评测任务 Runs</h3>
          </div>
          <RunsTable data={runs} />
        </section>
      </div>

      <section className="panel">
        <div className="section-heading-row">
          <h3>评测结果 Results</h3>
        </div>
        <ResultsTable data={results} />
      </section>

      <div className="grid two content-grid">
        <section className="panel">
          <div className="section-heading-row">
            <h3>失败用例 Failed Cases</h3>
          </div>
          <FailedCasesTable
            data={failedCases}
            convertingFailedCaseId={convertingFailedCaseId}
            onConvert={convertFailedCase}
          />
        </section>

        <section className="panel">
          <div className="section-heading-row">
            <h3>摘要 Summary</h3>
          </div>
          {summary ? (
            <>
              <div className="metric-row evaluation-card-grid">
                {regressionCards.map((card) => (
                  <MetricCard
                    key={card.key}
                    label={`${card.label} (${card.status})`}
                    value={card.value}
                  />
                ))}
              </div>
              <RegressionSummary summary={summary.summary.bad_case_regression} />
              <pre className="json-panel">{JSON.stringify(summary.summary, null, 2)}</pre>
            </>
          ) : (
            <p className="muted">请选择 run_id 加载评测摘要。</p>
          )}
        </section>
      </div>
    </>
  );
}

function DatasetTable({ data }: { data: EvaluationDatasetListResponse | null }) {
  const rows = data?.datasets ?? [];
  if (rows.length === 0) {
    return <p className="muted">暂无评测数据集。</p>;
  }
  return (
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>名称 Name</th>
          <th>类型 Type</th>
          <th>来源 Source</th>
          <th>创建时间 Created</th>
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
    return <p className="muted">暂无评测任务。</p>;
  }
  return (
    <table>
      <thead>
        <tr>
          <th>评测任务 Evaluation Run</th>
          <th>Run</th>
          <th>数据集 Dataset</th>
          <th>类型 Type</th>
          <th>状态 Status</th>
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
    return <p className="muted">暂无评测结果。请先运行本地 demo validation 或评测任务。</p>;
  }
  return (
    <table>
      <thead>
        <tr>
          <th>评测任务 Evaluation Run</th>
          <th>Run</th>
          <th>数据集 Dataset</th>
          <th>类型 Type</th>
          <th>指标 Metric</th>
          <th>数值 Value</th>
              <th>状态 Status</th>
              <th>原因 Reason</th>
              <th>详情 Details</th>
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
              <td className="evaluation-status-cell">
                <span className={`status-pill status-${statusClassName(summary.statusLabel)}`}>
                  {buildInsufficientDataLabel(result)}
                </span>
              </td>
              <td>{summary.reason}</td>
              <td>
                <pre className="json-panel compact-json">
                  {buildEvaluationResultJson(result)}
                </pre>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function FailedCasesTable({
  data,
  convertingFailedCaseId,
  onConvert
}: {
  data: EvaluationFailedCaseListResponse | null;
  convertingFailedCaseId: string | null;
  onConvert: (failedCaseId: string) => void;
}) {
  const rows = buildFailedCaseRows(data?.items ?? []);
  if (rows.length === 0) {
    return <p className="muted">暂无失败用例。</p>;
  }
  return (
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Run</th>
          <th>类型 Type</th>
          <th>模块 Module</th>
          <th>建议类型 Suggested</th>
          <th>创建时间 Created</th>
          <th>操作 Action</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((failedCase) => (
          <tr key={failedCase.failedCaseId}>
            <td>{failedCase.failedCaseId}</td>
            <td>{failedCase.runId}</td>
            <td>{failedCase.failureType}</td>
            <td>{failedCase.module}</td>
            <td>{failedCase.suggestedBadCaseType}</td>
            <td>{failedCase.createdAt}</td>
            <td>
              <button
                type="button"
                onClick={() => onConvert(failedCase.failedCaseId)}
                disabled={convertingFailedCaseId === failedCase.failedCaseId}
              >
                创建坏例 Create Bad Case
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function RegressionSummary({ summary }: { summary: unknown }) {
  const display =
    typeof summary === "object" && summary !== null
      ? buildBadCaseRegressionDisplaySummary(summary as Record<string, unknown>)
      : buildBadCaseRegressionDisplaySummary(null);
  return (
    <div className="summary-strip">
      <div className="metric-row review-metric-row">
        <MetricCard label="回归总数 Regression total" value={display.totalCases} />
        <MetricCard label="未处理 Open" value={display.openCases} />
        <MetricCard label="已修复 Fixed" value={display.fixedCases} />
        <MetricCard label="通过率 Pass rate" value={display.regressionPassRate} />
      </div>
      <p className="muted">
        Status {display.statusLabel} | verified {display.verifiedCases} | ignored{" "}
        {display.ignoredCases} | reopened {display.reopenedCaseCount}
      </p>
      <p className="muted">MVP regression: {display.definition}</p>
    </div>
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
