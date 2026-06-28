import { useEffect, useState } from "react";

import { getAlert } from "../api/alerts";
import { createBadCaseFromReview } from "../api/badCases";
import {
  addFalseNegative,
  addReviewComment,
  confirmReviewEvent,
  getReviewEvent,
  ignoreReviewEvent,
  listReviewEvents,
  markReviewEventFalsePositive,
  requestReviewRuleRerun,
  resolveReviewEvent
} from "../api/review";
import ReviewDrawer from "../components/ReviewDrawer";
import type {
  FalseNegativeRequest,
  ReviewEventDetail,
  ReviewEventListResponse,
  ReviewEventSummary
} from "../types";
import {
  buildReviewEventDisplaySummary,
  buildReviewStatusCounts,
  normalizeReviewValue
} from "../utils/reviewMetrics";
import {
  buildReviewLink,
  normalizeReviewFiltersFromQuery,
  parseReviewQuery,
  type ReviewFilterState
} from "../utils/reviewNavigation";
import {
  buildBadCaseFromReviewRequest,
  buildReviewActionRequest,
  buildReviewCommentRequest,
  buildReviewSuccessMessage,
  type ReviewWorkflowAction,
  validateReviewWorkflowAction
} from "../utils/reviewWorkflow";

type SubmittingState = ReviewWorkflowAction | "false-negative" | null;

interface FalseNegativeFormState {
  run_id: string;
  expected_event_type: string;
  description: string;
  zone_id: string;
  track_id: string;
  start_frame: string;
  end_frame: string;
  start_time_ms: string;
  end_time_ms: string;
  reviewer: string;
}

interface ReviewCenterPageProps {
  locationSearch?: string;
}

const emptyFalseNegativeForm: FalseNegativeFormState = {
  run_id: "",
  expected_event_type: "",
  description: "",
  zone_id: "",
  track_id: "",
  start_frame: "",
  end_frame: "",
  start_time_ms: "",
  end_time_ms: "",
  reviewer: "local_reviewer"
};

export default function ReviewCenterPage({
  locationSearch = currentLocationSearch()
}: ReviewCenterPageProps) {
  const initialNavigation = normalizeReviewFiltersFromQuery(parseReviewQuery(locationSearch));
  const [runId, setRunId] = useState(initialNavigation.runId ?? "");
  const [status, setStatus] = useState(initialNavigation.status ?? "");
  const [eventType, setEventType] = useState(initialNavigation.eventType ?? "");
  const [eventsData, setEventsData] = useState<ReviewEventListResponse | null>(null);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(
    initialNavigation.eventId ?? null
  );
  const [detail, setDetail] = useState<ReviewEventDetail | null>(null);
  const [loadingEvents, setLoadingEvents] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [submitting, setSubmitting] = useState<SubmittingState>(null);
  const [error, setError] = useState("");
  const [detailError, setDetailError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [reviewer, setReviewer] = useState("local_reviewer");
  const [comment, setComment] = useState("");
  const [openedAlertId, setOpenedAlertId] = useState<string | null>(
    initialNavigation.alertId ?? null
  );
  const [falseNegativeForm, setFalseNegativeForm] =
    useState<FalseNegativeFormState>({
      ...emptyFalseNegativeForm,
      run_id: initialNavigation.runId ?? ""
    });

  const events = eventsData?.items ?? [];
  const counts = buildReviewStatusCounts(events);

  useEffect(() => {
    const navigation = normalizeReviewFiltersFromQuery(parseReviewQuery(locationSearch));
    setRunId(navigation.runId ?? "");
    setStatus(navigation.status ?? "");
    setEventType(navigation.eventType ?? "");
    setSelectedEventId(navigation.eventId ?? null);
    setOpenedAlertId(navigation.alertId ?? null);
    setFalseNegativeForm((current) => ({
      ...current,
      run_id: navigation.runId ?? ""
    }));

    if (navigation.alertId && (!navigation.runId || !navigation.eventId)) {
      resolveAlertContext(navigation.alertId, navigation);
      return;
    }
    if (navigation.runId) {
      loadEvents(navigation.eventId, {
        runId: navigation.runId,
        status: navigation.status ?? "",
        eventType: navigation.eventType ?? "",
        alertId: navigation.alertId ?? null
      });
      return;
    }

    setEventsData(null);
    setDetail(null);
    setError("");
    setDetailError("");
  }, [locationSearch]);

  async function resolveAlertContext(alertId: string, navigation: ReviewFilterState) {
    setDetailError("");
    try {
      const alert = await getAlert(alertId);
      const resolvedRunId = navigation.runId || alert.run_id;
      const resolvedEventId = navigation.eventId || alert.event_id;
      setRunId(resolvedRunId);
      setOpenedAlertId(alertId);
      if (resolvedEventId) {
        setSelectedEventId(resolvedEventId);
      }
      if (!resolvedRunId) {
        setDetailError(`Alert ${alertId} does not include a run_id.`);
        return;
      }
      if (!resolvedEventId) {
        await loadEvents(undefined, {
          runId: resolvedRunId,
          status: navigation.status ?? "",
          eventType: navigation.eventType ?? "",
          alertId
        });
        setDetailError(`Alert ${alertId} does not include a linked event_id.`);
        return;
      }
      await loadEvents(resolvedEventId, {
        runId: resolvedRunId,
        status: navigation.status ?? "",
        eventType: navigation.eventType ?? "",
        alertId
      });
    } catch (currentError) {
      setDetailError(
        currentError instanceof Error
          ? `Unable to load alert context ${alertId}: ${currentError.message}`
          : `Unable to load alert context ${alertId}.`
      );
      if (navigation.runId) {
        await loadEvents(navigation.eventId, {
          runId: navigation.runId,
          status: navigation.status ?? "",
          eventType: navigation.eventType ?? "",
          alertId
        });
      }
    }
  }

  async function loadEvents(
    preferredEventId?: string,
    overrides: {
      runId?: string;
      status?: string;
      eventType?: string;
      alertId?: string | null;
    } = {}
  ) {
    const normalizedRunId = (overrides.runId ?? runId).trim();
    const nextStatus = overrides.status ?? status;
    const nextEventType = overrides.eventType ?? eventType;
    const nextAlertId = overrides.alertId !== undefined ? overrides.alertId : openedAlertId;
    setSuccessMessage("");
    setDetailError("");
    syncReviewUrl({
      runId: normalizedRunId,
      eventId: normalizedRunId ? preferredEventId ?? selectedEventId : undefined,
      alertId: nextAlertId,
      status: nextStatus,
      eventType: nextEventType
    });
    if (!normalizedRunId) {
      setError("Enter a run_id to load review events.");
      setEventsData(null);
      setSelectedEventId(null);
      setDetail(null);
      return;
    }

    setLoadingEvents(true);
    setError("");
    try {
      const payload = await listReviewEvents({
        run_id: normalizedRunId,
        status: normalizeOptionalString(nextStatus),
        event_type: normalizeOptionalString(nextEventType),
        limit: 100,
        offset: 0
      });
      setEventsData(payload);
      const nextEventId = preferredEventId || chooseNextEventId(payload.items, selectedEventId);
      setSelectedEventId(nextEventId);
      if (nextEventId) {
        await loadEventDetail(nextEventId, normalizedRunId);
      } else {
        setDetail(null);
      }
    } catch (currentError) {
      setEventsData(null);
      setSelectedEventId(null);
      setDetail(null);
      setError(currentError instanceof Error ? currentError.message : "Review events request failed");
    } finally {
      setLoadingEvents(false);
    }
  }

  async function loadEventDetail(eventId: string, runIdOverride = runId.trim()) {
    if (!runIdOverride) {
      setDetailError("Enter a run_id before loading event detail.");
      return;
    }

    setLoadingDetail(true);
    setDetailError("");
    try {
      setDetail(await getReviewEvent(eventId, { run_id: runIdOverride }));
    } catch (currentError) {
      setDetail(null);
      setDetailError(currentError instanceof Error ? currentError.message : "Review detail request failed");
    } finally {
      setLoadingDetail(false);
    }
  }

  async function runReviewWorkflowAction(action: ReviewWorkflowAction) {
    const currentEventId = selectedEventId;
    const normalizedRunId = runId.trim();
    const form = {
      runId: normalizedRunId,
      eventId: currentEventId,
      reviewer,
      comment,
      alertId: openedAlertId
    };
    const validation = validateReviewWorkflowAction(action, form);
    if (!validation.valid) {
      setDetailError(validation.message);
      return;
    }
    const eventId = currentEventId ?? "";

    const actionMap = {
      confirm: confirmReviewEvent,
      "false-positive": markReviewEventFalsePositive,
      ignore: ignoreReviewEvent,
      resolve: resolveReviewEvent
    };

    setSubmitting(action);
    setDetailError("");
    setSuccessMessage("");
    try {
      if (action === "comment") {
        const response = await addReviewComment(buildReviewCommentRequest(form));
        setComment("");
        setSuccessMessage(buildReviewSuccessMessage(action, response));
        await loadEvents(eventId);
        return;
      }
      if (action === "bad-case") {
        if (!detail) {
          throw new Error("Select an event before creating a Bad Case.");
        }
        const response = await createBadCaseFromReview(
          buildBadCaseFromReviewRequest(detail, form)
        );
        setSuccessMessage(buildReviewSuccessMessage(action, response));
        await loadEvents(eventId);
        return;
      }
      if (action === "rerun-rule") {
        const response = await requestReviewRuleRerun(
          eventId,
          buildReviewActionRequest(form)
        );
        setComment("");
        setSuccessMessage(buildReviewSuccessMessage(action, response));
        await loadEvents(eventId);
        return;
      }
      const response = await actionMap[action](eventId, buildReviewActionRequest(form));
      setComment("");
      setSuccessMessage(buildReviewSuccessMessage(action, response));
      await loadEvents(eventId);
    } catch (currentError) {
      setDetailError(
        currentError instanceof Error ? currentError.message : "Review action failed"
      );
    } finally {
      setSubmitting(null);
    }
  }

  async function submitFalseNegative() {
    setSubmitting("false-negative");
    setError("");
    setSuccessMessage("");
    try {
      const payload = buildFalseNegativePayload(falseNegativeForm, runId);
      const response = await addFalseNegative(payload);
      setFalseNegativeForm({
        ...emptyFalseNegativeForm,
        run_id: payload.run_id,
        reviewer: payload.reviewer ?? "local_reviewer"
      });
      setSuccessMessage(`漏报已保存：${response.false_negative.false_negative_id}`);
      if (payload.run_id === runId.trim()) {
        await loadEvents(selectedEventId ?? undefined);
      }
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "False negative request failed");
    } finally {
      setSubmitting(null);
    }
  }

  function updateRunId(value: string) {
    setRunId(value);
    setFalseNegativeForm((current) => ({
      ...current,
      run_id: current.run_id || value
    }));
  }

  return (
    <>
      <header className="page-header">
        <div>
          <h2>复核中心</h2>
          <p>人工确认事件、标记误报/漏报，并沉淀复核记录。</p>
        </div>
      </header>

      <section className="panel">
        <div className="form-grid">
          <label>
            Run ID
            <input
              placeholder="run_..."
              value={runId}
              onChange={(event) => updateRunId(event.target.value)}
            />
          </label>
          <label>
            状态
            <select value={status} onChange={(event) => setStatus(event.target.value)}>
              <option value="">全部</option>
              <option value="pending">待复核</option>
              <option value="confirmed">已确认</option>
              <option value="false_positive">误报</option>
              <option value="false_negative">漏报</option>
              <option value="ignored">已忽略</option>
              <option value="resolved">已解决</option>
            </select>
          </label>
          <label>
            事件类型
            <input
              placeholder="all"
              value={eventType}
              onChange={(event) => setEventType(event.target.value)}
            />
          </label>
          <button type="button" onClick={() => loadEvents()} disabled={loadingEvents}>
            刷新
          </button>
        </div>
        <div className="metric-row review-metric-row">
          <Metric label="待复核" value={counts.pending} />
          <Metric label="已确认" value={counts.confirmed} />
          <Metric label="误报" value={counts.false_positive} />
          <Metric label="已解决" value={counts.resolved} />
        </div>
        {successMessage ? <p className="alert-box success">{successMessage}</p> : null}
        {error ? <p className="alert-box error">{error}</p> : null}
        {loadingEvents ? <p className="muted">正在加载复核事件...</p> : null}
        {!loadingEvents && !eventsData ? (
          <p className="empty-state">请输入 run_id 并刷新，开始复核事件。</p>
        ) : null}
        {!loadingEvents && eventsData && events.length === 0 ? (
          <p className="empty-state">暂无匹配的复核事件。</p>
        ) : null}
      </section>

      <div className="grid two content-grid review-workspace">
        <section className="panel">
          <div className="section-heading-row">
            <h3>事件列表</h3>
            {eventsData ? <span className="muted">{eventsData.total} 条</span> : null}
          </div>
          {events.length > 0 ? (
            <div className="table-scroll">
              <table className="data-table">
                <caption className="sr-only">复核事件列表</caption>
                <thead>
                  <tr>
                    <th scope="col">事件</th>
                    <th scope="col">状态</th>
                    <th scope="col">原状态</th>
                    <th scope="col">类型</th>
                    <th scope="col">严重程度</th>
                    <th scope="col">Track</th>
                    <th scope="col">区域</th>
                    <th scope="col">帧</th>
                    <th scope="col">告警</th>
                    <th scope="col">评论</th>
                    <th scope="col">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((event) => (
                    <ReviewEventRow
                      key={event.event_id}
                      event={event}
                      selected={selectedEventId === event.event_id}
                      onOpen={() => {
                        setSelectedEventId(event.event_id);
                        loadEventDetail(event.event_id);
                      }}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="muted">暂无事件列表。请先运行一次视频分析。</p>
          )}
        </section>

        <ReviewDrawer
          detail={detail}
          openedAlertId={openedAlertId}
          loading={loadingDetail}
          error={detailError}
          reviewer={reviewer}
          comment={comment}
          submitting={submitting}
          onReviewerChange={setReviewer}
          onCommentChange={setComment}
          onAction={runReviewWorkflowAction}
        />
      </div>

      <section className="panel">
        <div className="section-heading-row">
          <h3>添加漏报</h3>
          <span className="muted">仅记录本地复核产物</span>
        </div>
        <div className="form-grid">
          <label>
            Run ID
            <input
              value={falseNegativeForm.run_id}
              onChange={(event) => updateFalseNegativeField("run_id", event.target.value)}
            />
          </label>
          <label>
            期望事件类型
            <input
              value={falseNegativeForm.expected_event_type}
              onChange={(event) =>
                updateFalseNegativeField("expected_event_type", event.target.value)
              }
            />
          </label>
          <label>
            复核人
            <input
              value={falseNegativeForm.reviewer}
              onChange={(event) => updateFalseNegativeField("reviewer", event.target.value)}
            />
          </label>
          <label>
            区域
            <input
              value={falseNegativeForm.zone_id}
              onChange={(event) => updateFalseNegativeField("zone_id", event.target.value)}
            />
          </label>
          <label>
            Track
            <input
              type="number"
              value={falseNegativeForm.track_id}
              onChange={(event) => updateFalseNegativeField("track_id", event.target.value)}
            />
          </label>
          <label>
            起始帧
            <input
              type="number"
              value={falseNegativeForm.start_frame}
              onChange={(event) => updateFalseNegativeField("start_frame", event.target.value)}
            />
          </label>
          <label>
            结束帧
            <input
              type="number"
              value={falseNegativeForm.end_frame}
              onChange={(event) => updateFalseNegativeField("end_frame", event.target.value)}
            />
          </label>
          <label>
            起始 ms
            <input
              type="number"
              value={falseNegativeForm.start_time_ms}
              onChange={(event) => updateFalseNegativeField("start_time_ms", event.target.value)}
            />
          </label>
          <label>
            结束 ms
            <input
              type="number"
              value={falseNegativeForm.end_time_ms}
              onChange={(event) => updateFalseNegativeField("end_time_ms", event.target.value)}
            />
          </label>
        </div>
        <label className="stacked-control">
          描述
          <textarea
            rows={3}
            value={falseNegativeForm.description}
            onChange={(event) => updateFalseNegativeField("description", event.target.value)}
          />
        </label>
        <button type="button" disabled={submitting !== null} onClick={submitFalseNegative}>
          添加漏报
        </button>
      </section>
    </>
  );

  function updateFalseNegativeField(field: keyof FalseNegativeFormState, value: string) {
    setFalseNegativeForm((current) => ({ ...current, [field]: value }));
  }
}

function ReviewEventRow({
  event,
  selected,
  onOpen
}: {
  event: ReviewEventSummary;
  selected: boolean;
  onOpen: () => void;
}) {
  const summary = buildReviewEventDisplaySummary(event);
  return (
    <tr className={selected ? "selected-row" : ""}>
      <td className="cell-id">{summary.eventId}</td>
      <td>
        <span className={`status-pill status-${event.review_status}`}>
          {summary.statusLabel}
        </span>
      </td>
      <td>{summary.originalStatus}</td>
      <td>{summary.eventType}</td>
      <td>{normalizeReviewValue(event.severity)}</td>
      <td>{summary.track}</td>
      <td className="cell-id">{summary.zone}</td>
      <td>{summary.frameRange}</td>
      <td>{summary.linkedAlertCount}</td>
      <td>{summary.commentCount}</td>
      <td>
        <button type="button" onClick={onOpen}>
          打开
        </button>
      </td>
    </tr>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="card metric-card">
      <span className="metric-value">{value}</span>
      <span className="muted">{label}</span>
    </div>
  );
}

function normalizeOptionalString(value: string): string | undefined {
  const trimmed = value.trim();
  return trimmed ? trimmed : undefined;
}

function chooseNextEventId(
  events: ReviewEventSummary[],
  preferredEventId: string | null | undefined
): string | null {
  if (preferredEventId && events.some((event) => event.event_id === preferredEventId)) {
    return preferredEventId;
  }
  return events[0]?.event_id ?? null;
}

function buildFalseNegativePayload(
  form: FalseNegativeFormState,
  currentRunId: string
): FalseNegativeRequest {
  const run_id = form.run_id.trim() || currentRunId.trim();
  const expected_event_type = form.expected_event_type.trim();
  const description = form.description.trim();
  if (!run_id) {
    throw new Error("run_id is required for false negative records.");
  }
  if (!expected_event_type) {
    throw new Error("expected_event_type is required.");
  }
  if (!description) {
    throw new Error("description is required.");
  }
  return {
    run_id,
    expected_event_type,
    description,
    reviewer: form.reviewer.trim() || "local_reviewer",
    zone_id: normalizeNullableString(form.zone_id),
    track_id: parseOptionalInteger(form.track_id, "track_id"),
    start_frame: parseOptionalInteger(form.start_frame, "start_frame"),
    end_frame: parseOptionalInteger(form.end_frame, "end_frame"),
    start_time_ms: parseOptionalInteger(form.start_time_ms, "start_time_ms"),
    end_time_ms: parseOptionalInteger(form.end_time_ms, "end_time_ms")
  };
}

function normalizeNullableString(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function parseOptionalInteger(value: string, label: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = Number(trimmed);
  if (!Number.isInteger(parsed)) {
    throw new Error(`${label} must be an integer.`);
  }
  return parsed;
}

function syncReviewUrl({
  runId,
  eventId,
  alertId,
  status,
  eventType
}: {
  runId?: string | null;
  eventId?: string | null;
  alertId?: string | null;
  status?: string | null;
  eventType?: string | null;
}) {
  if (window.location.pathname !== "/review") {
    return;
  }
  const href = buildReviewLink(runId, eventId, alertId, {
    status,
    event_type: eventType
  });
  if (`${window.location.pathname}${window.location.search}` !== href) {
    window.history.replaceState(null, "", href);
  }
}

function currentLocationSearch(): string {
  return window.location.search;
}
