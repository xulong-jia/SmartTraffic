import { type MouseEvent, useEffect, useState } from "react";

import {
  acknowledgeAlert,
  ignoreAlert,
  listAlerts,
  resolveAlert
} from "../api/alerts";
import type { AlertCenterResponse, AlertRecord } from "../types";
import { buildReviewLink } from "../utils/reviewNavigation";

interface AlertCenterPageProps {
  onOpenReview?: (href: string) => void;
}

export default function AlertCenterPage({ onOpenReview }: AlertCenterPageProps) {
  const [runId, setRunId] = useState("");
  const [status, setStatus] = useState("");
  const [level, setLevel] = useState("");
  const [acknowledgedBy, setAcknowledgedBy] = useState("");
  const [data, setData] = useState<AlertCenterResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [actionAlertId, setActionAlertId] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    loadAlerts();
  }, []);

  async function loadAlerts() {
    setLoading(true);
    setError("");
    try {
      const payload = await listAlerts({
        runId: normalizeOptionalString(runId),
        status: normalizeOptionalString(status),
        level: normalizeOptionalString(level)
      });
      setData(payload);
    } catch (currentError) {
      setData(null);
      setError(currentError instanceof Error ? currentError.message : "Alerts request failed");
    } finally {
      setLoading(false);
    }
  }

  async function runAction(
    alertId: string,
    action: (id: string) => Promise<AlertRecord>
  ) {
    setActionAlertId(alertId);
    setError("");
    try {
      await action(alertId);
      await loadAlerts();
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Alert update failed");
    } finally {
      setActionAlertId(null);
    }
  }

  return (
    <>
      <header className="page-header">
        <div>
          <h2>Alert Center</h2>
          <p>事件告警状态</p>
        </div>
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
            Status
            <select value={status} onChange={(event) => setStatus(event.target.value)}>
              <option value="">All</option>
              <option value="new">New</option>
              <option value="acknowledged">Acknowledged</option>
              <option value="resolved">Resolved</option>
              <option value="ignored">Ignored</option>
            </select>
          </label>
          <label>
            Level
            <select value={level} onChange={(event) => setLevel(event.target.value)}>
              <option value="">All</option>
              <option value="critical">Critical</option>
              <option value="warning">Warning</option>
              <option value="info">Info</option>
            </select>
          </label>
          <label>
            Operator
            <input
              placeholder="operator"
              value={acknowledgedBy}
              onChange={(event) => setAcknowledgedBy(event.target.value)}
            />
          </label>
          <button type="button" onClick={loadAlerts} disabled={loading}>
            Refresh
          </button>
        </div>
        {error ? <p className="muted">{error}</p> : null}
        {loading ? <p className="muted">Loading alerts</p> : null}
        {!loading && data && data.alerts.length === 0 ? (
          <p className="muted">No alerts match the current filters.</p>
        ) : null}
        {data && data.alerts.length > 0 ? (
          <table>
            <thead>
              <tr>
                <th>Status</th>
                <th>Level</th>
                <th>Type</th>
                <th>Event</th>
                <th>Track</th>
                <th>Run</th>
                <th>Message</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.alerts.map((alert) => (
                <tr key={alert.id}>
                  <td>{alert.status}</td>
                  <td>{alert.level}</td>
                  <td>{alert.alert_type}</td>
                  <td>{alert.event_id}</td>
                  <td>{formatNullable(alert.track_id)}</td>
                  <td>{alert.run_id}</td>
                  <td>{alert.message}</td>
                  <td>
                    <div className="toolbar compact">
                      <button
                        type="button"
                        disabled={actionAlertId === alert.id || alert.status === "acknowledged"}
                        onClick={() =>
                          runAction(alert.id, (id) =>
                            acknowledgeAlert(id, normalizeOptionalString(acknowledgedBy) ?? undefined)
                          )
                        }
                      >
                        Acknowledge
                      </button>
                      <button
                        type="button"
                        disabled={actionAlertId === alert.id || alert.status === "resolved"}
                        onClick={() => runAction(alert.id, resolveAlert)}
                      >
                        Resolve
                      </button>
                      <button
                        type="button"
                        disabled={actionAlertId === alert.id || alert.status === "ignored"}
                        onClick={() => runAction(alert.id, ignoreAlert)}
                      >
                        Ignore
                      </button>
                      {alert.event_id ? (
                        <a
                          href={buildReviewLink(
                            alert.run_id,
                            alert.event_id,
                            alert.alert_id || alert.id
                          )}
                          onClick={(clickEvent) =>
                            openReviewLink(
                              clickEvent,
                              buildReviewLink(
                                alert.run_id,
                                alert.event_id,
                                alert.alert_id || alert.id
                              ),
                              onOpenReview
                            )
                          }
                        >
                          Review linked event
                        </a>
                      ) : (
                        <span className="muted">No linked event</span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </section>
    </>
  );
}

function normalizeOptionalString(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function formatNullable(value: string | number | null | undefined): string {
  return value === null || value === undefined || value === "" ? "-" : String(value);
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
  onOpenReview(href);
}
