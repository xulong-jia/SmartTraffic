import { useEffect, useState } from "react";

import { getAlert } from "../api/alerts";
import {
  addFalseNegative,
  addReviewComment,
  confirmReviewEvent,
  getReviewEvent,
  ignoreReviewEvent,
  listReviewEvents,
  markReviewEventFalsePositive,
  resolveReviewEvent
} from "../api/review";
import type {
  FalseNegativeRequest,
  ReviewActionRequest,
  ReviewEventDetail,
  ReviewEventListResponse,
  ReviewEventSummary
} from "../types";
import {
  buildReviewEventDisplaySummary,
  buildReviewStatusCounts,
  formatReviewStatusLabel,
  normalizeReviewValue
} from "../utils/reviewMetrics";
import {
  buildReviewLink,
  normalizeReviewFiltersFromQuery,
  parseReviewQuery,
  type ReviewFilterState
} from "../utils/reviewNavigation";

type ReviewSubmitAction = "confirm" | "false-positive" | "ignore" | "resolve";
type SubmittingState = ReviewSubmitAction | "comment" | "false-negative" | null;

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

  async function runReviewAction(action: ReviewSubmitAction) {
    const currentEventId = selectedEventId;
    const normalizedRunId = runId.trim();
    if (!currentEventId || !normalizedRunId) {
      setDetailError("Select an event and run_id before submitting a review action.");
      return;
    }

    const body: ReviewActionRequest = {
      run_id: normalizedRunId,
      comment: comment.trim(),
      reviewer: reviewer.trim() || "local_reviewer",
      alert_id: openedAlertId
    };
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
      await actionMap[action](currentEventId, body);
      setComment("");
      setSuccessMessage(`Review action saved: ${action}`);
      await loadEvents(currentEventId);
    } catch (currentError) {
      setDetailError(currentError instanceof Error ? currentError.message : "Review action failed");
    } finally {
      setSubmitting(null);
    }
  }

  async function submitComment() {
    const currentEventId = selectedEventId;
    const normalizedRunId = runId.trim();
    const trimmedComment = comment.trim();
    if (!currentEventId || !normalizedRunId) {
      setDetailError("Select an event and run_id before adding a comment.");
      return;
    }
    if (!trimmedComment) {
      setDetailError("Comment is required.");
      return;
    }

    setSubmitting("comment");
    setDetailError("");
    setSuccessMessage("");
    try {
      await addReviewComment({
        run_id: normalizedRunId,
        event_id: currentEventId,
        comment: trimmedComment,
        reviewer: reviewer.trim() || "local_reviewer",
        alert_id: openedAlertId
      });
      setComment("");
      setSuccessMessage("Comment added.");
      await loadEvents(currentEventId);
    } catch (currentError) {
      setDetailError(currentError instanceof Error ? currentError.message : "Comment request failed");
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
      setSuccessMessage(`False negative saved: ${response.false_negative.false_negative_id}`);
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
          <h2>Review Center</h2>
          <p>Artifact-backed event review workflow for the Stage 7 MVP.</p>
        </div>
      </header>

      <section className="panel">
        <div className="toolbar">
          <label>
            Run ID
            <input
              placeholder="run_..."
              value={runId}
              onChange={(event) => updateRunId(event.target.value)}
            />
          </label>
          <label>
            Status
            <select value={status} onChange={(event) => setStatus(event.target.value)}>
              <option value="">All</option>
              <option value="pending">Pending</option>
              <option value="confirmed">Confirmed</option>
              <option value="false_positive">False positive</option>
              <option value="false_negative">False negative</option>
              <option value="ignored">Ignored</option>
              <option value="resolved">Resolved</option>
            </select>
          </label>
          <label>
            Event type
            <input
              placeholder="all"
              value={eventType}
              onChange={(event) => setEventType(event.target.value)}
            />
          </label>
          <button type="button" onClick={() => loadEvents()} disabled={loadingEvents}>
            Refresh
          </button>
        </div>
        <div className="metric-row review-metric-row">
          <Metric label="Pending" value={counts.pending} />
          <Metric label="Confirmed" value={counts.confirmed} />
          <Metric label="False positive" value={counts.false_positive} />
          <Metric label="Resolved" value={counts.resolved} />
        </div>
        {successMessage ? <p className="muted">{successMessage}</p> : null}
        {error ? <p className="muted">{error}</p> : null}
        {loadingEvents ? <p className="muted">Loading review events</p> : null}
        {!loadingEvents && !eventsData ? (
          <p className="muted">Enter a run_id and refresh to review events.</p>
        ) : null}
        {!loadingEvents && eventsData && events.length === 0 ? (
          <p className="muted">No review events match the current filters.</p>
        ) : null}
      </section>

      <div className="grid two review-workspace">
        <section className="panel">
          <div className="section-heading-row">
            <h3>Events</h3>
            {eventsData ? <span className="muted">{eventsData.total} total</span> : null}
          </div>
          {events.length > 0 ? (
            <table>
              <thead>
                <tr>
                  <th>Event</th>
                  <th>Status</th>
                  <th>Original</th>
                  <th>Type</th>
                  <th>Severity</th>
                  <th>Track</th>
                  <th>Zone</th>
                  <th>Frames</th>
                  <th>Alerts</th>
                  <th>Comments</th>
                  <th>Action</th>
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
          ) : (
            <p className="muted">No event list loaded.</p>
          )}
        </section>

        <section className="panel">
          <div className="section-heading-row">
            <h3>Event Detail</h3>
            {loadingDetail ? <span className="muted">Loading</span> : null}
          </div>
          {detailError ? <p className="muted">{detailError}</p> : null}
          {!detail && !loadingDetail ? (
            <p className="muted">Select an event to inspect review state, comments, alerts, and artifact references.</p>
          ) : null}
          {detail ? (
            <>
              <ReviewEventDetailPanel detail={detail} openedAlertId={openedAlertId} />
              <section className="summary-strip">
                <h3>Review Actions</h3>
                <div className="toolbar compact">
                  <label>
                    Reviewer
                    <input
                      value={reviewer}
                      onChange={(event) => setReviewer(event.target.value)}
                    />
                  </label>
                </div>
                <label className="stacked-control">
                  Comment
                  <textarea
                    rows={4}
                    value={comment}
                    onChange={(event) => setComment(event.target.value)}
                  />
                </label>
                <div className="toolbar compact">
                  <button
                    type="button"
                    disabled={submitting !== null}
                    onClick={() => runReviewAction("confirm")}
                  >
                    Confirm
                  </button>
                  <button
                    type="button"
                    disabled={submitting !== null}
                    onClick={() => runReviewAction("false-positive")}
                  >
                    Mark false positive
                  </button>
                  <button
                    type="button"
                    disabled={submitting !== null}
                    onClick={() => runReviewAction("ignore")}
                  >
                    Ignore
                  </button>
                  <button
                    type="button"
                    disabled={submitting !== null}
                    onClick={() => runReviewAction("resolve")}
                  >
                    Resolve
                  </button>
                  <button type="button" disabled={submitting !== null} onClick={submitComment}>
                    Add comment
                  </button>
                </div>
                {submitting ? <p className="muted">Submitting {submitting}</p> : null}
              </section>
              <CommentsList detail={detail} />
            </>
          ) : null}
        </section>
      </div>

      <section className="panel">
        <div className="section-heading-row">
          <h3>Add False Negative</h3>
          <span className="muted">MVP review artifact only</span>
        </div>
        <div className="toolbar">
          <label>
            Run ID
            <input
              value={falseNegativeForm.run_id}
              onChange={(event) => updateFalseNegativeField("run_id", event.target.value)}
            />
          </label>
          <label>
            Expected event type
            <input
              value={falseNegativeForm.expected_event_type}
              onChange={(event) =>
                updateFalseNegativeField("expected_event_type", event.target.value)
              }
            />
          </label>
          <label>
            Reviewer
            <input
              value={falseNegativeForm.reviewer}
              onChange={(event) => updateFalseNegativeField("reviewer", event.target.value)}
            />
          </label>
          <label>
            Zone
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
            Start frame
            <input
              type="number"
              value={falseNegativeForm.start_frame}
              onChange={(event) => updateFalseNegativeField("start_frame", event.target.value)}
            />
          </label>
          <label>
            End frame
            <input
              type="number"
              value={falseNegativeForm.end_frame}
              onChange={(event) => updateFalseNegativeField("end_frame", event.target.value)}
            />
          </label>
          <label>
            Start ms
            <input
              type="number"
              value={falseNegativeForm.start_time_ms}
              onChange={(event) => updateFalseNegativeField("start_time_ms", event.target.value)}
            />
          </label>
          <label>
            End ms
            <input
              type="number"
              value={falseNegativeForm.end_time_ms}
              onChange={(event) => updateFalseNegativeField("end_time_ms", event.target.value)}
            />
          </label>
        </div>
        <label className="stacked-control">
          Description
          <textarea
            rows={3}
            value={falseNegativeForm.description}
            onChange={(event) => updateFalseNegativeField("description", event.target.value)}
          />
        </label>
        <button type="button" disabled={submitting !== null} onClick={submitFalseNegative}>
          Add false negative
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
      <td>{summary.eventId}</td>
      <td>
        <span className={`status-pill status-${event.review_status}`}>
          {summary.statusLabel}
        </span>
      </td>
      <td>{summary.originalStatus}</td>
      <td>{summary.eventType}</td>
      <td>{normalizeReviewValue(event.severity)}</td>
      <td>{summary.track}</td>
      <td>{summary.zone}</td>
      <td>{summary.frameRange}</td>
      <td>{summary.linkedAlertCount}</td>
      <td>{summary.commentCount}</td>
      <td>
        <button type="button" onClick={onOpen}>
          Open
        </button>
      </td>
    </tr>
  );
}

function ReviewEventDetailPanel({
  detail,
  openedAlertId
}: {
  detail: ReviewEventDetail;
  openedAlertId: string | null;
}) {
  const event = detail.event;
  return (
    <>
      {openedAlertId ? (
        <p className="muted">Opened from alert: {openedAlertId}</p>
      ) : null}
      <dl className="detail-grid">
        <DetailItem label="Event ID" value={event.event_id} />
        <DetailItem label="Run ID" value={detail.run_id} />
        <DetailItem label="Event type" value={event.event_type} />
        <DetailItem label="Review status" value={formatReviewStatusLabel(event.review_status)} />
        <DetailItem label="Original status" value={event.original_status} />
        <DetailItem label="Severity" value={event.severity} />
        <DetailItem label="Track" value={event.track_id} />
        <DetailItem label="Zone" value={event.zone_id} />
        <DetailItem label="Start frame" value={event.start_frame} />
        <DetailItem label="End frame" value={event.end_frame} />
        <DetailItem label="Start ms" value={event.start_time_ms} />
        <DetailItem label="End ms" value={event.end_time_ms} />
        <DetailItem label="Comments" value={event.comment_count} />
        <DetailItem label="Last action" value={event.last_action} />
      </dl>

      <section className="summary-strip">
        <h3>Linked Alerts</h3>
        {detail.linked_alerts.length === 0 ? (
          <p className="muted">No linked alerts.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Alert</th>
                <th>Status</th>
                <th>Level</th>
                <th>Message</th>
              </tr>
            </thead>
            <tbody>
              {detail.linked_alerts.map((alert) => (
                <tr
                  className={isOpenedAlert(alert, openedAlertId) ? "selected-row" : ""}
                  key={alert.alert_id || alert.id}
                >
                  <td>{alert.alert_id || alert.id}</td>
                  <td>{alert.status}</td>
                  <td>{alert.level}</td>
                  <td>{alert.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="summary-strip">
        <h3>Visual Artifacts</h3>
        <dl className="detail-grid">
          <DetailItem label="Keyframes" value={artifactField(detail.visual_artifacts, "keyframes", "status")} />
          <DetailItem label="Keyframes path" value={artifactField(detail.visual_artifacts, "keyframes", "path")} />
          <DetailItem label="Annotated video" value={artifactField(detail.visual_artifacts, "annotated_video", "status")} />
          <DetailItem label="Video path" value={artifactField(detail.visual_artifacts, "annotated_video", "path")} />
        </dl>
      </section>
    </>
  );
}

function CommentsList({ detail }: { detail: ReviewEventDetail }) {
  return (
    <section className="summary-strip">
      <h3>Comments</h3>
      {detail.comments.length === 0 ? (
        <p className="muted">No review comments.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Action</th>
              <th>After</th>
              <th>Reviewer</th>
              <th>Comment</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {detail.comments.map((item) => (
              <tr key={item.review_id}>
                <td>{item.action}</td>
                <td>{item.after_status}</td>
                <td>{item.reviewer}</td>
                <td>{item.comment || "-"}</td>
                <td>{item.created_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
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

function DetailItem({ label, value }: { label: string; value: unknown }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{formatDetailValue(value)}</dd>
    </div>
  );
}

function formatDetailValue(value: unknown): string {
  if (typeof value === "string" || typeof value === "number") {
    return normalizeReviewValue(value);
  }
  if (typeof value === "boolean") {
    return String(value);
  }
  return "-";
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

function artifactField(
  artifacts: Record<string, unknown>,
  artifactKey: string,
  field: string
): string {
  const artifact = artifacts[artifactKey];
  if (isRecord(artifact)) {
    const value = artifact[field];
    return typeof value === "string" || typeof value === "number" ? String(value) : "-";
  }
  return "-";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
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

function isOpenedAlert(
  alert: { alert_id?: string | null; id?: string | null },
  openedAlertId: string | null
): boolean {
  if (!openedAlertId) {
    return false;
  }
  return alert.alert_id === openedAlertId || alert.id === openedAlertId;
}

function currentLocationSearch(): string {
  return window.location.search;
}
