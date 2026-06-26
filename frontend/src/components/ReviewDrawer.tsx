import type { ReviewEventDetail } from "../types";
import {
  REVIEW_WORKFLOW_ACTIONS,
  type ReviewWorkflowAction
} from "../utils/reviewWorkflow";
import { formatReviewStatusLabel, normalizeReviewValue } from "../utils/reviewMetrics";

interface ReviewDrawerProps {
  detail: ReviewEventDetail | null;
  openedAlertId: string | null;
  loading: boolean;
  error: string;
  reviewer: string;
  comment: string;
  submitting: ReviewWorkflowAction | "false-negative" | null;
  onReviewerChange: (value: string) => void;
  onCommentChange: (value: string) => void;
  onAction: (action: ReviewWorkflowAction) => void;
}

export default function ReviewDrawer({
  detail,
  openedAlertId,
  loading,
  error,
  reviewer,
  comment,
  submitting,
  onReviewerChange,
  onCommentChange,
  onAction
}: ReviewDrawerProps) {
  return (
    <section className="panel review-drawer" aria-label="Review drawer">
      <div className="section-heading-row">
        <h3>Review Drawer</h3>
        {loading ? <span className="muted">Loading</span> : null}
      </div>
      {error ? <p className="status-pill status-error">{error}</p> : null}
      {!detail && !loading ? (
        <p className="muted">
          Select an event to inspect review state, comments, alerts, and artifact references.
        </p>
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
                  onChange={(event) => onReviewerChange(event.target.value)}
                />
              </label>
            </div>
            <label className="stacked-control">
              Comment
              <textarea
                rows={4}
                value={comment}
                onChange={(event) => onCommentChange(event.target.value)}
              />
            </label>
            <div className="review-action-grid">
              {REVIEW_WORKFLOW_ACTIONS.map((item) => (
                <button
                  key={item.action}
                  type="button"
                  disabled={submitting !== null}
                  onClick={() => onAction(item.action)}
                  title={item.description}
                >
                  {item.label}
                </button>
              ))}
            </div>
            {submitting ? <p className="muted">Submitting {submitting}</p> : null}
          </section>
          <CommentsList detail={detail} />
        </>
      ) : null}
    </section>
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
      {openedAlertId ? <p className="muted">Opened from alert: {openedAlertId}</p> : null}
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
          <DetailItem
            label="Keyframes"
            value={artifactField(detail.visual_artifacts, "keyframes", "status")}
          />
          <DetailItem
            label="Keyframes path"
            value={artifactField(detail.visual_artifacts, "keyframes", "path")}
          />
          <DetailItem
            label="Annotated video"
            value={artifactField(detail.visual_artifacts, "annotated_video", "status")}
          />
          <DetailItem
            label="Video path"
            value={artifactField(detail.visual_artifacts, "annotated_video", "path")}
          />
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

function isOpenedAlert(
  alert: { alert_id?: string | null; id?: string | null },
  openedAlertId: string | null
): boolean {
  if (!openedAlertId) {
    return false;
  }
  return alert.alert_id === openedAlertId || alert.id === openedAlertId;
}
