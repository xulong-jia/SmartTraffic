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
        <h3>复核详情</h3>
        {loading ? <span className="muted">加载中</span> : null}
      </div>
      {error ? <p className="alert-box error">{error}</p> : null}
      {!detail && !loading ? (
        <p className="empty-state">
          请选择事件，查看复核状态、评论、告警和产物引用。
        </p>
      ) : null}
      {detail ? (
        <>
          <ReviewEventDetailPanel detail={detail} openedAlertId={openedAlertId} />
          <section className="summary-strip">
            <h3>复核操作</h3>
            <div className="toolbar compact">
              <label>
                复核人
                <input
                  value={reviewer}
                  onChange={(event) => onReviewerChange(event.target.value)}
                />
              </label>
            </div>
            <label className="stacked-control">
              评论
              <textarea
                rows={4}
                value={comment}
                onChange={(event) => onCommentChange(event.target.value)}
              />
            </label>
            <div className="review-action-grid button-group">
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
            {submitting ? <p className="muted">正在提交 {submitting}</p> : null}
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
      {openedAlertId ? <p className="muted">来自告警：{openedAlertId}</p> : null}
      <dl className="detail-grid">
        <DetailItem label="Event ID" value={event.event_id} />
        <DetailItem label="Run ID" value={detail.run_id} />
        <DetailItem label="事件类型" value={event.event_type} />
        <DetailItem label="复核状态" value={formatReviewStatusLabel(event.review_status)} />
        <DetailItem label="原状态" value={event.original_status} />
        <DetailItem label="严重程度" value={event.severity} />
        <DetailItem label="Track" value={event.track_id} />
        <DetailItem label="Zone" value={event.zone_id} />
        <DetailItem label="起始帧" value={event.start_frame} />
        <DetailItem label="结束帧" value={event.end_frame} />
        <DetailItem label="起始 ms" value={event.start_time_ms} />
        <DetailItem label="结束 ms" value={event.end_time_ms} />
        <DetailItem label="评论数" value={event.comment_count} />
        <DetailItem label="最近操作" value={event.last_action} />
      </dl>

      <section className="summary-strip">
        <h3>关联告警</h3>
        {detail.linked_alerts.length === 0 ? (
          <p className="muted">暂无关联告警。</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>告警</th>
                <th>状态</th>
                <th>级别</th>
                <th>消息</th>
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
        <h3>可视化产物</h3>
        <dl className="detail-grid">
          <DetailItem
            label="关键帧"
            value={artifactField(detail.visual_artifacts, "keyframes", "status")}
          />
          <DetailItem
            label="关键帧路径"
            value={artifactField(detail.visual_artifacts, "keyframes", "path")}
          />
          <DetailItem
            label="标注视频"
            value={artifactField(detail.visual_artifacts, "annotated_video", "status")}
          />
          <DetailItem
            label="视频路径"
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
      <h3>评论</h3>
      {detail.comments.length === 0 ? (
        <p className="muted">暂无复核评论。</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>操作</th>
              <th>之后状态</th>
              <th>复核人</th>
              <th>评论</th>
              <th>创建时间</th>
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
