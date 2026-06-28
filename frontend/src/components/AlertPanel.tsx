import type { MouseEvent } from "react";

import type { AlertRecord } from "../types";
import {
  alertPanelEmptyLabel,
  buildAlertActionPayload,
  buildAlertPanelRows,
  filterAlertPanelRows,
  type AlertActionPayload
} from "../utils/alertPanel";

interface AlertPanelProps {
  alerts: AlertRecord[];
  loading?: boolean;
  error?: string;
  statusFilter?: string | null;
  levelFilter?: string | null;
  selectedAlertId?: string | null;
  actionAlertId?: string | null;
  onSelectAlert?: (alert: AlertRecord) => void;
  onAcknowledge?: (payload: AlertActionPayload) => void;
  onResolve?: (payload: AlertActionPayload) => void;
  onIgnore?: (payload: AlertActionPayload) => void;
  buildReviewHref?: (alert: AlertRecord) => string | null;
  onOpenReview?: (href: string) => void;
}

export default function AlertPanel({
  alerts,
  loading = false,
  error = "",
  statusFilter = "",
  levelFilter = "",
  selectedAlertId = null,
  actionAlertId = null,
  onSelectAlert,
  onAcknowledge,
  onResolve,
  onIgnore,
  buildReviewHref,
  onOpenReview
}: AlertPanelProps) {
  const visibleAlerts = filterAlertPanelRows(alerts, {
    status: statusFilter,
    level: levelFilter
  });
  const rows = buildAlertPanelRows(visibleAlerts, selectedAlertId);
  const emptyLabel = alertPanelEmptyLabel(loading, error, visibleAlerts);

  return (
    <div>
      {emptyLabel ? <p className={error ? "alert-box error" : "empty-state"}>{emptyLabel}</p> : null}
      {rows.length > 0 ? (
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>状态</th>
                <th>级别</th>
                <th>标题</th>
                <th>事件</th>
                <th>Track</th>
                <th>Run</th>
                <th>创建时间</th>
                <th>消息</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => {
                const alert = visibleAlerts[index];
                const href = buildReviewHref?.(alert) ?? null;
                const busy = actionAlertId === row.id || actionAlertId === alert.id;
                return (
                  <tr
                    className={row.selected ? "selected-row" : ""}
                    key={row.id}
                    onClick={() => onSelectAlert?.(alert)}
                  >
                    <td>
                      <span className={`status-pill status-${statusClassName(alert.status)}`}>
                        {row.status}
                      </span>
                    </td>
                    <td>
                      <span className={`status-pill status-${statusClassName(alert.level)}`}>
                        {row.level}
                      </span>
                    </td>
                    <td>{row.title}</td>
                    <td className="cell-id">{row.eventId}</td>
                    <td>{row.trackId}</td>
                    <td className="cell-id">{row.runId}</td>
                    <td>{row.createdAt}</td>
                    <td className="wrap-cell">{row.message}</td>
                    <td>
                      <div className="button-group">
                        {onAcknowledge ? (
                          <button
                            disabled={busy || !row.canAcknowledge}
                            onClick={(event) => {
                              event.stopPropagation();
                              onAcknowledge(buildAlertActionPayload(row.id, "acknowledge"));
                            }}
                            type="button"
                          >
                            确认
                          </button>
                        ) : null}
                        {onResolve ? (
                          <button
                            disabled={busy || !row.canResolve}
                            onClick={(event) => {
                              event.stopPropagation();
                              onResolve(buildAlertActionPayload(row.id, "resolve"));
                            }}
                            type="button"
                          >
                            解决
                          </button>
                        ) : null}
                        {onIgnore ? (
                          <button
                            disabled={busy || !row.canIgnore}
                            onClick={(event) => {
                              event.stopPropagation();
                              onIgnore(buildAlertActionPayload(row.id, "ignore"));
                            }}
                            type="button"
                          >
                            忽略
                          </button>
                        ) : null}
                        {href ? (
                          <a
                            href={href}
                            onClick={(event) => openReviewLink(event, href, onOpenReview)}
                          >
                            复核关联事件
                          </a>
                        ) : (
                          <span className="muted">无关联事件</span>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}

function openReviewLink(
  event: MouseEvent<HTMLAnchorElement>,
  href: string,
  onOpenReview?: (href: string) => void
) {
  if (!onOpenReview || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
    return;
  }
  event.preventDefault();
  event.stopPropagation();
  onOpenReview(href);
}

function statusClassName(value: string | number | undefined | null): string {
  const raw = String(value ?? "unknown")
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, "_");
  return raw || "unknown";
}
