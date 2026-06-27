import { type Dispatch, type SetStateAction, useEffect, useState } from "react";

import {
  createBadCase,
  getBadCase,
  listBadCases,
  updateBadCase
} from "../api/badCases";
import type {
  BadCaseCreateRequest,
  BadCaseListResponse,
  BadCaseRecord,
  BadCaseUpdateRequest
} from "../types";
import {
  BAD_CASE_MODULE_KEYS,
  BAD_CASE_STATUS_KEYS,
  BAD_CASE_TYPE_KEYS,
  buildBadCaseDisplaySummary,
  formatBadCaseModuleLabel,
  formatBadCaseStatusLabel,
  formatBadCaseTypeLabel,
  normalizeBadCaseTags,
  normalizeBadCaseValue
} from "../utils/badCaseMetrics";

interface BadCaseFormState {
  run_id: string;
  case_type: string;
  module: string;
  description: string;
  expected_result: string;
  actual_result: string;
  root_cause: string;
  event_id: string;
  track_id: string;
  frame_index: string;
  tags: string;
  snapshot_path: string;
}

interface UpdateFormState {
  status: string;
  root_cause: string;
  tags: string;
  description: string;
}

const emptyCreateForm: BadCaseFormState = {
  run_id: "",
  case_type: "false_positive",
  module: "event_engine",
  description: "",
  expected_result: "",
  actual_result: "",
  root_cause: "",
  event_id: "",
  track_id: "",
  frame_index: "",
  tags: "",
  snapshot_path: ""
};

const emptyUpdateForm: UpdateFormState = {
  status: "open",
  root_cause: "",
  tags: "",
  description: ""
};

export default function BadCaseCenterPage() {
  const [runId, setRunId] = useState("");
  const [caseType, setCaseType] = useState("");
  const [module, setModule] = useState("");
  const [status, setStatus] = useState("");
  const [tag, setTag] = useState("");
  const [data, setData] = useState<BadCaseListResponse | null>(null);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [detail, setDetail] = useState<BadCaseRecord | null>(null);
  const [createForm, setCreateForm] = useState<BadCaseFormState>(emptyCreateForm);
  const [updateForm, setUpdateForm] = useState<UpdateFormState>(emptyUpdateForm);
  const [loading, setLoading] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [submitting, setSubmitting] = useState<"create" | "update" | null>(null);
  const [error, setError] = useState("");
  const [detailError, setDetailError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const cases = data?.items ?? [];
  const summary = data?.summary;

  useEffect(() => {
    loadCases();
  }, []);

  async function loadCases(preferredCaseId = selectedCaseId) {
    setLoading(true);
    setError("");
    setSuccessMessage("");
    try {
      const payload = await listBadCases({
        run_id: normalizeOptionalParam(runId),
        case_type: normalizeOptionalParam(caseType),
        module: normalizeOptionalParam(module),
        status: normalizeOptionalParam(status),
        tag: normalizeOptionalParam(tag),
        limit: 100,
        offset: 0
      });
      setData(payload);
      const nextCaseId = preferredCaseId || payload.items[0]?.case_id || null;
      setSelectedCaseId(nextCaseId);
      if (nextCaseId) {
        const matched = payload.items.find((item) => item.case_id === nextCaseId);
        await loadDetail(nextCaseId, matched?.run_id);
      } else {
        setDetail(null);
      }
    } catch (currentError) {
      setData(null);
      setSelectedCaseId(null);
      setDetail(null);
      setError(currentError instanceof Error ? currentError.message : "Bad Case request failed");
    } finally {
      setLoading(false);
    }
  }

  async function loadDetail(caseId: string, runIdOverride?: string) {
    setLoadingDetail(true);
    setDetailError("");
    try {
      const record = await getBadCase(caseId, {
        run_id: normalizeOptionalString(runIdOverride ?? runId) ?? undefined
      });
      setDetail(record);
      setSelectedCaseId(record.case_id);
      setUpdateForm({
        status: record.status || "open",
        root_cause: record.root_cause || "",
        tags: record.tags.join(", "),
        description: record.description || ""
      });
    } catch (currentError) {
      setDetail(null);
      setDetailError(
        currentError instanceof Error ? currentError.message : "Bad Case detail request failed"
      );
    } finally {
      setLoadingDetail(false);
    }
  }

  async function submitCreate() {
    const normalizedRunId = createForm.run_id.trim();
    if (!normalizedRunId) {
      setError("run_id is required.");
      return;
    }
    setSubmitting("create");
    setError("");
    setSuccessMessage("");
    try {
      const created = await createBadCase(buildCreateRequest(createForm));
      setCreateForm({ ...emptyCreateForm, run_id: normalizedRunId });
      setSuccessMessage(`Created ${created.case_id}.`);
      await loadCases(created.case_id);
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Bad Case create failed");
    } finally {
      setSubmitting(null);
    }
  }

  async function submitUpdate() {
    if (!detail) {
      setDetailError("Select a Bad Case before updating.");
      return;
    }
    setSubmitting("update");
    setDetailError("");
    setSuccessMessage("");
    try {
      const body: BadCaseUpdateRequest = {
        run_id: detail.run_id,
        status: updateForm.status,
        root_cause: updateForm.root_cause,
        tags: normalizeBadCaseTags(updateForm.tags),
        description: updateForm.description
      };
      const updated = await updateBadCase(detail.case_id, body);
      setDetail(updated);
      setSuccessMessage(`Updated ${updated.case_id}.`);
      await loadCases(updated.case_id);
    } catch (currentError) {
      setDetailError(currentError instanceof Error ? currentError.message : "Bad Case update failed");
    } finally {
      setSubmitting(null);
    }
  }

  return (
    <>
      <header className="page-header">
        <div>
          <h2>坏例中心 Bad Case Center</h2>
          <p>记录误报、漏报、ID 切换、轨迹丢失和规则错误。</p>
        </div>
        <button type="button" onClick={() => loadCases()} disabled={loading}>
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
            类型 Type
            <select value={caseType} onChange={(event) => setCaseType(event.target.value)}>
              <option value="">全部 All</option>
              {BAD_CASE_TYPE_KEYS.map((value) => (
                <option key={value} value={value}>
                  {formatBadCaseTypeLabel(value)}
                </option>
              ))}
            </select>
          </label>
          <label>
            模块 Module
            <select value={module} onChange={(event) => setModule(event.target.value)}>
              <option value="">全部 All</option>
              {BAD_CASE_MODULE_KEYS.map((value) => (
                <option key={value} value={value}>
                  {formatBadCaseModuleLabel(value)}
                </option>
              ))}
            </select>
          </label>
          <label>
            状态 Status
            <select value={status} onChange={(event) => setStatus(event.target.value)}>
              <option value="">全部 All</option>
              {BAD_CASE_STATUS_KEYS.map((value) => (
                <option key={value} value={value}>
                  {formatBadCaseStatusLabel(value)}
                </option>
              ))}
            </select>
          </label>
          <label>
            标签 Tag
            <input value={tag} onChange={(event) => setTag(event.target.value)} />
          </label>
          <button type="button" onClick={() => loadCases()} disabled={loading}>
            应用 Apply
          </button>
        </div>
        {error ? <p className="alert-box error">{error}</p> : null}
        {successMessage ? <p className="alert-box success">{successMessage}</p> : null}
        {loading ? <p className="muted">正在加载坏例...</p> : null}
        {summary ? (
          <div className="metric-row review-metric-row">
            <MetricCard label="总数 Total" value={String(summary.total)} />
            <MetricCard label="未处理 Open" value={String(summary.by_status.open ?? 0)} />
            <MetricCard label="已修复 Fixed" value={String(summary.by_status.fixed ?? 0)} />
            <MetricCard label="主要类型 Top Type" value={topEntryLabel(summary.by_type)} />
          </div>
        ) : null}
        {summary ? (
          <div className="summary-strip">
            <p>
              模块 Modules: {topEntries(summary.by_module)} | 标签 Tags: {topEntries(summary.by_tag)}
            </p>
          </div>
        ) : null}
        {!loading && data && cases.length === 0 ? (
          <p className="empty-state">暂无坏例。复核误报、漏报或评测失败后可生成坏例。</p>
        ) : null}
        {cases.length > 0 ? (
          <table>
            <thead>
              <tr>
                <th>坏例 Case</th>
                <th>Run</th>
                <th>类型 Type</th>
                <th>模块 Module</th>
                <th>状态 Status</th>
                <th>事件 Event</th>
                <th>Track</th>
                <th>帧 Frame</th>
                <th>标签 Tags</th>
                <th>来源 Source</th>
                <th>失败用例 Failed Case</th>
                <th>更新时间 Updated</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((badCase) => {
                const display = buildBadCaseDisplaySummary(badCase);
                return (
                  <tr
                    key={badCase.case_id}
                    className={selectedCaseId === badCase.case_id ? "selected-row" : ""}
                  >
                    <td>
                      <button
                        type="button"
                        onClick={() => loadDetail(badCase.case_id, badCase.run_id)}
                      >
                        {display.caseId}
                      </button>
                    </td>
                    <td>{display.runId}</td>
                    <td>{display.caseType}</td>
                    <td>{display.module}</td>
                    <td>
                      <span className={`status-pill status-${badCase.status}`}>
                        {display.statusLabel}
                      </span>
                    </td>
                    <td>{display.event}</td>
                    <td>{display.track}</td>
                    <td>{display.frame}</td>
                    <td>{display.tags}</td>
                    <td>{display.source}</td>
                    <td>{display.linkedFailedCaseId}</td>
                    <td>{display.updatedAt}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : null}
      </section>

      <section className="grid two content-grid bad-case-workspace">
        <div className="panel">
          <div className="section-heading-row">
            <h3>详情 Detail</h3>
            {loadingDetail ? <span className="muted">加载中 Loading</span> : null}
          </div>
          {detailError ? <p className="alert-box error">{detailError}</p> : null}
          {detail ? (
            <>
              <dl className="detail-grid">
                <DetailItem label="Case ID" value={detail.case_id} />
                <DetailItem label="Run ID" value={detail.run_id} />
                <DetailItem label="描述 Description" value={detail.description} />
                <DetailItem label="期望 Expected" value={detail.expected_result} />
                <DetailItem label="实际 Actual" value={detail.actual_result} />
                <DetailItem label="根因 Root cause" value={detail.root_cause} />
                <DetailItem label="快照 Snapshot" value={detail.snapshot_path} />
                <DetailItem label="复核 Review" value={detail.linked_review_id} />
                <DetailItem label="失败用例 Failed Case" value={detail.linked_failed_case_id} />
                <DetailItem label="事件 Event" value={detail.event_id} />
                <DetailItem label="Track" value={detail.track_id} />
                <DetailItem label="帧 Frame" value={detail.frame_index} />
                <DetailItem label="创建时间 Created" value={detail.created_at} />
                <DetailItem label="更新时间 Updated" value={detail.updated_at} />
              </dl>
              <div className="summary-strip">
                <label className="stacked-control">
                  状态 Status
                  <select
                    value={updateForm.status}
                    onChange={(event) =>
                      setUpdateForm((current) => ({ ...current, status: event.target.value }))
                    }
                  >
                    {BAD_CASE_STATUS_KEYS.map((value) => (
                      <option key={value} value={value}>
                        {formatBadCaseStatusLabel(value)}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="stacked-control">
                  根因 Root cause
                  <textarea
                    rows={2}
                    value={updateForm.root_cause}
                    onChange={(event) =>
                      setUpdateForm((current) => ({
                        ...current,
                        root_cause: event.target.value
                      }))
                    }
                  />
                </label>
                <label className="stacked-control">
                  标签 Tags
                  <input
                    value={updateForm.tags}
                    onChange={(event) =>
                      setUpdateForm((current) => ({ ...current, tags: event.target.value }))
                    }
                  />
                </label>
                <label className="stacked-control">
                  描述 Description
                  <textarea
                    rows={2}
                    value={updateForm.description}
                    onChange={(event) =>
                      setUpdateForm((current) => ({
                        ...current,
                        description: event.target.value
                      }))
                    }
                  />
                </label>
                <button
                  type="button"
                  onClick={submitUpdate}
                  disabled={submitting === "update"}
                >
                  更新 Update
                </button>
              </div>
            </>
          ) : (
            <p className="empty-state">请选择一个坏例 Bad Case。</p>
          )}
        </div>

        <div className="panel">
          <h3>创建坏例 Create</h3>
          <div className="grid two">
            <TextInput label="Run ID" field="run_id" form={createForm} setForm={setCreateForm} />
            <label className="stacked-control">
              类型 Type
              <select
                value={createForm.case_type}
                onChange={(event) => updateCreateField("case_type", event.target.value)}
              >
                {BAD_CASE_TYPE_KEYS.map((value) => (
                  <option key={value} value={value}>
                    {formatBadCaseTypeLabel(value)}
                  </option>
                ))}
              </select>
            </label>
            <label className="stacked-control">
              模块 Module
              <select
                value={createForm.module}
                onChange={(event) => updateCreateField("module", event.target.value)}
              >
                {BAD_CASE_MODULE_KEYS.map((value) => (
                  <option key={value} value={value}>
                    {formatBadCaseModuleLabel(value)}
                  </option>
                ))}
              </select>
            </label>
            <TextInput label="Event ID" field="event_id" form={createForm} setForm={setCreateForm} />
            <TextInput label="Track ID" field="track_id" form={createForm} setForm={setCreateForm} />
            <TextInput
              label="Frame"
              field="frame_index"
              form={createForm}
              setForm={setCreateForm}
            />
            <TextInput label="Tags" field="tags" form={createForm} setForm={setCreateForm} />
            <TextInput
              label="Snapshot"
              field="snapshot_path"
              form={createForm}
              setForm={setCreateForm}
            />
          </div>
          <label className="stacked-control">
            描述 Description
            <textarea
              rows={2}
              value={createForm.description}
              onChange={(event) => updateCreateField("description", event.target.value)}
            />
          </label>
          <label className="stacked-control">
            期望 Expected
            <textarea
              rows={2}
              value={createForm.expected_result}
              onChange={(event) => updateCreateField("expected_result", event.target.value)}
            />
          </label>
          <label className="stacked-control">
            实际 Actual
            <textarea
              rows={2}
              value={createForm.actual_result}
              onChange={(event) => updateCreateField("actual_result", event.target.value)}
            />
          </label>
          <label className="stacked-control">
            根因 Root cause
            <textarea
              rows={2}
              value={createForm.root_cause}
              onChange={(event) => updateCreateField("root_cause", event.target.value)}
            />
          </label>
          <button type="button" onClick={submitCreate} disabled={submitting === "create"}>
            创建 Create
          </button>
        </div>
      </section>
    </>
  );

  function updateCreateField(field: keyof BadCaseFormState, value: string) {
    setCreateForm((current) => ({ ...current, [field]: value }));
  }
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-card card">
      <span className="metric-value">{value}</span>
      <span className="muted">{label}</span>
    </div>
  );
}

function DetailItem({
  label,
  value
}: {
  label: string;
  value: string | number | null | undefined;
}) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{normalizeBadCaseValue(value)}</dd>
    </div>
  );
}

function TextInput({
  label,
  field,
  form,
  setForm
}: {
  label: string;
  field: keyof BadCaseFormState;
  form: BadCaseFormState;
  setForm: Dispatch<SetStateAction<BadCaseFormState>>;
}) {
  return (
    <label className="stacked-control">
      {label}
      <input
        value={form[field]}
        onChange={(event) =>
          setForm((current) => ({ ...current, [field]: event.target.value }))
        }
      />
    </label>
  );
}

function buildCreateRequest(form: BadCaseFormState): BadCaseCreateRequest {
  return {
    run_id: form.run_id.trim(),
    case_type: form.case_type,
    module: form.module,
    description: form.description,
    expected_result: form.expected_result,
    actual_result: form.actual_result,
    root_cause: form.root_cause,
    event_id: normalizeOptionalString(form.event_id),
    track_id: parseOptionalInteger(form.track_id),
    frame_index: parseOptionalInteger(form.frame_index),
    tags: normalizeBadCaseTags(form.tags),
    snapshot_path: normalizeOptionalString(form.snapshot_path),
    source: "manual"
  };
}

function normalizeOptionalString(value: string | null | undefined): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed : null;
}

function normalizeOptionalParam(value: string | null | undefined): string | undefined {
  return normalizeOptionalString(value) ?? undefined;
}

function parseOptionalInteger(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = Number.parseInt(trimmed, 10);
  return Number.isNaN(parsed) ? null : parsed;
}

function topEntryLabel(entries: Record<string, number>): string {
  const [key, count] = Object.entries(entries).sort((left, right) => right[1] - left[1])[0] ?? [];
  return key ? `${formatBadCaseTypeLabel(key)} (${count})` : "-";
}

function topEntries(entries: Record<string, number>): string {
  const formatted = Object.entries(entries)
    .sort((left, right) => right[1] - left[1])
    .slice(0, 3)
    .map(([key, count]) => `${key}:${count}`);
  return formatted.length ? formatted.join(", ") : "-";
}
