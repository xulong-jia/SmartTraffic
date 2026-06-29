import { useEffect, useState } from "react";

import {
  acknowledgeAlert,
  ignoreAlert,
  listAlerts,
  resolveAlert
} from "../api/alerts";
import AlertPanel from "../components/AlertPanel";
import type { AlertCenterResponse, AlertRecord } from "../types";
import type { AlertActionPayload } from "../utils/alertPanel";
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
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);
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
    <div className="alert-center-page">
      <header className="page-header">
        <div>
          <h2>告警中心</h2>
          <p>查看事件告警，并进行确认、忽略或解决。</p>
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
            状态
            <select value={status} onChange={(event) => setStatus(event.target.value)}>
              <option value="">全部</option>
              <option value="new">新告警</option>
              <option value="acknowledged">已确认</option>
              <option value="resolved">已解决</option>
              <option value="ignored">已忽略</option>
            </select>
          </label>
          <label>
            级别
            <select value={level} onChange={(event) => setLevel(event.target.value)}>
              <option value="">全部</option>
              <option value="critical">严重</option>
              <option value="warning">警告</option>
              <option value="info">信息</option>
            </select>
          </label>
          <label>
            操作人
            <input
              placeholder="operator"
              value={acknowledgedBy}
              onChange={(event) => setAcknowledgedBy(event.target.value)}
            />
          </label>
          <button type="button" onClick={loadAlerts} disabled={loading}>
            刷新
          </button>
        </div>
        <AlertPanel
          actionAlertId={actionAlertId}
          alerts={data?.alerts ?? []}
          buildReviewHref={(alert) =>
            alert.event_id
              ? buildReviewLink(alert.run_id, alert.event_id, alert.alert_id || alert.id)
              : null
          }
          error={error}
          levelFilter={level}
          loading={loading}
          onAcknowledge={(payload) =>
            runAlertPanelAction(payload, (id) =>
              acknowledgeAlert(id, normalizeOptionalString(acknowledgedBy) ?? undefined)
            )
          }
          onIgnore={(payload) => runAlertPanelAction(payload, ignoreAlert)}
          onOpenReview={onOpenReview}
          onResolve={(payload) => runAlertPanelAction(payload, resolveAlert)}
          onSelectAlert={(alert) => setSelectedAlertId(alert.alert_id || alert.id)}
          selectedAlertId={selectedAlertId}
          statusFilter={status}
        />
      </section>
    </div>
  );

  function runAlertPanelAction(
    payload: AlertActionPayload,
    action: (id: string) => Promise<AlertRecord>
  ) {
    runAction(payload.alertId, action);
  }
}

function normalizeOptionalString(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}
