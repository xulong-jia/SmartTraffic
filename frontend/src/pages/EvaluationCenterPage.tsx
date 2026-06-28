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
import CollapsibleSection from "../components/CollapsibleSection";
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
  extractMetricStatus,
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
      setSuccessMessage(`已注册 ${created.dataset_id}。`);
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
      setSuccessMessage(`已完成 ${response.evaluation_run.evaluation_run_id}。`);
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
      setSuccessMessage(`已从 ${failedCaseId} 创建 ${created.case_id}。`);
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
          <h2>评测中心</h2>
          <p>查看检测、跟踪、轨迹、事件和流量统计的本地评测结果。</p>
        </div>
        <button type="button" onClick={() => loadEvaluationState()} disabled={loading}>
          刷新
        </button>
      </header>

      <section className="panel evaluation-control-card">
        <div className="toolbar evaluation-toolbar">
          <label>
            Run ID
            <input
              placeholder="run_..."
              value={runId}
              onChange={(event) => setRunId(event.target.value)}
            />
          </label>
          <label>
            数据集
            <select value={datasetId} onChange={(event) => setDatasetId(event.target.value)}>
              <option value="">无</option>
              {(datasets?.datasets ?? []).map((dataset) => (
                <option key={dataset.dataset_id} value={dataset.dataset_id}>
                  {dataset.dataset_id}
                </option>
              ))}
            </select>
          </label>
          <label>
            类型
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
            运行评测
          </button>
          <button type="button" onClick={() => loadEvaluationState()} disabled={loading}>
            应用
          </button>
        </div>
        {loading ? <p className="muted">正在加载评测...</p> : null}
        {error ? <p className="alert-box error">{error}</p> : null}
        {successMessage ? (
          <p className="alert-box success">{successMessage}</p>
        ) : null}
        <div className="summary-grid evaluation-summary-grid">
          <MetricCard label="结果" value={String(results?.total ?? 0)} />
          <MetricCard label="可用" value={String(statusCounts.available)} />
          <MetricCard label="数据不足" value={String(statusCounts.insufficient_data)} />
          <MetricCard label="失败用例" value={String(failedCases?.total ?? 0)} />
        </div>
        <div className="info-callout">
          <h3>评测边界</h3>
          <ul className="compact-list">
            {EVALUATION_BOUNDARY_NOTICES.map((notice) => (
              <li key={notice.key}>
                <strong>{notice.label}:</strong> {notice.detail}
              </li>
            ))}
          </ul>
          <p>
            <strong>不适用：</strong>
            当前评测缺少 expected labels，因此该指标不参与通过/失败判断。
          </p>
          <p>
            <strong>数据不足：</strong>
            缺少标注或回放数据，不等于模型失败。
          </p>
          <p className="muted">{formatEvaluationBoundaryForType(String(evaluationType))}</p>
        </div>
        {metricCards.length > 0 ? (
          <div className="summary-grid evaluation-card-grid">
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

      <div className="page-grid-2 evaluation-dataset-grid">
        <section className="panel table-section card-fill evaluation-dataset-card">
          <div className="section-heading-row">
            <h3>数据集</h3>
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
              名称
              <input
                value={datasetForm.name}
                onChange={(event) =>
                  setDatasetForm({ ...datasetForm, name: event.target.value })
                }
              />
            </label>
            <label>
              类型
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
              期望事件
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
              期望计数
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
              注册
            </button>
          </div>
          <DatasetTable data={datasets} />
        </section>

        <section className="panel table-section card-fill evaluation-runs-card">
          <div className="section-heading-row">
            <h3>评测任务</h3>
          </div>
          <RunsTable data={runs} />
        </section>
      </div>

      <section className="panel table-section table-card evaluation-results-card">
        <div className="section-heading-row">
          <h3>评测结果</h3>
        </div>
        <ResultsTable data={results} />
      </section>

      <div className="page-grid-2 evaluation-outcome-grid">
        <section className="panel table-section card-fill evaluation-failed-card">
          <div className="section-heading-row">
            <h3>失败用例</h3>
          </div>
          <FailedCasesTable
            data={failedCases}
            convertingFailedCaseId={convertingFailedCaseId}
            onConvert={convertFailedCase}
          />
        </section>

        <section className="panel card-fill evaluation-summary-panel">
          <div className="section-heading-row">
            <h3>摘要</h3>
          </div>
          {summary ? (
            <>
              <div className="summary-grid evaluation-card-grid">
                {regressionCards.map((card) => (
                  <MetricCard
                    key={card.key}
                    label={`${card.label} (${card.status})`}
                    value={card.value}
                  />
                ))}
              </div>
              <RegressionSummary summary={summary.summary.bad_case_regression} />
              <CollapsibleSection title="摘要 JSON" className="compact-section">
                <pre className="json-panel evaluation-json-panel">
                  {JSON.stringify(summary.summary, null, 2)}
                </pre>
              </CollapsibleSection>
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
      <caption className="sr-only">评测数据集列表</caption>
      <thead>
        <tr>
          <th scope="col">ID</th>
          <th scope="col">名称</th>
          <th scope="col">类型</th>
          <th scope="col">来源</th>
          <th scope="col">创建时间</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((dataset) => (
          <tr key={dataset.dataset_id}>
            <td className="cell-id">{dataset.dataset_id}</td>
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
      <caption className="sr-only">评测任务列表</caption>
      <thead>
        <tr>
          <th scope="col">评测任务</th>
          <th scope="col">Run</th>
          <th scope="col">数据集</th>
          <th scope="col">类型</th>
          <th scope="col">状态</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((run) => (
          <tr key={run.evaluation_run_id}>
            <td className="cell-id">{run.evaluation_run_id}</td>
            <td className="cell-id">{run.run_id}</td>
            <td className="cell-id">{run.dataset_id || "-"}</td>
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
      <caption className="sr-only">评测结果列表</caption>
      <thead>
        <tr>
          <th scope="col">评测任务</th>
          <th scope="col">Run</th>
          <th scope="col">数据集</th>
          <th scope="col">类型</th>
          <th scope="col">指标</th>
          <th scope="col">数值</th>
          <th scope="col">状态</th>
          <th scope="col">原因</th>
          <th scope="col">详情</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((result) => {
          const summary = buildEvaluationResultDisplaySummary(result);
          return (
            <tr key={result.evaluation_result_id}>
              <td className="cell-id">{summary.evaluationRunId}</td>
              <td className="cell-id">{summary.runId}</td>
              <td className="cell-id">{summary.datasetId}</td>
              <td>{summary.evaluationType}</td>
              <td>{summary.metricName}</td>
              <td>{summary.metricValue}</td>
              <td className="evaluation-status-cell">
                <span className={`status-pill status-${statusClassName(extractMetricStatus(result))}`}>
                  {buildInsufficientDataLabel(result)}
                </span>
              </td>
              <td>{summary.reason}</td>
              <td>
                <details className="inline-details">
                  <summary>查看 JSON</summary>
                  <pre className="json-panel compact-json">
                    {buildEvaluationResultJson(result)}
                  </pre>
                </details>
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
      <caption className="sr-only">评测失败用例列表</caption>
      <thead>
        <tr>
          <th scope="col">ID</th>
          <th scope="col">Run</th>
          <th scope="col">类型</th>
          <th scope="col">模块</th>
          <th scope="col">建议类型</th>
          <th scope="col">创建时间</th>
          <th scope="col">操作</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((failedCase) => (
          <tr key={failedCase.failedCaseId}>
            <td className="cell-id">{failedCase.failedCaseId}</td>
            <td className="cell-id">{failedCase.runId}</td>
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
                创建坏例
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
        <MetricCard label="回归总数" value={display.totalCases} />
        <MetricCard label="未处理" value={display.openCases} />
        <MetricCard label="已修复" value={display.fixedCases} />
        <MetricCard label="通过率" value={display.regressionPassRate} />
      </div>
      <p className="muted">
        状态 {display.statusLabel} | 已验证 {display.verifiedCases} | 已忽略{" "}
        {display.ignoredCases} | 重开 {display.reopenedCaseCount}
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
