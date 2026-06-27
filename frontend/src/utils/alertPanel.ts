import type { AlertRecord } from "../types";

export type AlertPanelAction = "acknowledge" | "resolve" | "ignore";

export interface AlertPanelFilters {
  status?: string | null;
  level?: string | null;
}

export interface AlertPanelRow {
  id: string;
  title: string;
  message: string;
  level: string;
  status: string;
  eventId: string;
  runId: string;
  trackId: string;
  createdAt: string;
  selected: boolean;
  canAcknowledge: boolean;
  canResolve: boolean;
  canIgnore: boolean;
}

export interface AlertActionPayload {
  alertId: string;
  action: AlertPanelAction;
}

export function filterAlertPanelRows(
  alerts: AlertRecord[],
  filters: AlertPanelFilters = {}
): AlertRecord[] {
  const status = normalizeFilter(filters.status);
  const level = normalizeFilter(filters.level);
  return alerts.filter((alert) => {
    if (status && normalizeFilter(alert.status) !== status) {
      return false;
    }
    if (level && normalizeFilter(alert.level) !== level) {
      return false;
    }
    return true;
  });
}

export function buildAlertPanelRows(
  alerts: AlertRecord[],
  selectedAlertId: string | null = null
): AlertPanelRow[] {
  return alerts.map((alert) => {
    const id = alert.alert_id || alert.id;
    return {
      id,
      title: normalizeText(alert.title) || normalizeDisplay(alert.alert_type),
      message: normalizeDisplay(alert.message),
      level: formatAlertLevelLabel(alert.level),
      status: formatAlertStatusLabel(alert.status),
      eventId: normalizeDisplay(alert.event_id),
      runId: normalizeDisplay(alert.run_id),
      trackId: formatOptional(alert.track_id),
      createdAt: normalizeDisplay(alert.created_at),
      selected: id === selectedAlertId || alert.id === selectedAlertId,
      canAcknowledge: alert.status !== "acknowledged",
      canResolve: alert.status !== "resolved",
      canIgnore: alert.status !== "ignored"
    };
  });
}

export function buildAlertActionPayload(
  alertId: string,
  action: AlertPanelAction
): AlertActionPayload {
  return { alertId, action };
}

export function alertPanelEmptyLabel(
  loading: boolean,
  error: string,
  alerts: AlertRecord[]
): string {
  if (loading) {
    return "正在加载告警...";
  }
  if (error) {
    return error;
  }
  if (alerts.length === 0) {
    return "暂无告警。事件触发后会在这里显示。";
  }
  return "";
}

export function formatAlertStatusLabel(status: string | null | undefined): string {
  const normalized = normalizeText(status);
  const labels: Record<string, string> = {
    new: "新告警 new",
    acknowledged: "已确认 acknowledged",
    resolved: "已解决 resolved",
    ignored: "已忽略 ignored"
  };
  return labels[normalized] ?? normalizeDisplay(status);
}

export function formatAlertLevelLabel(level: string | null | undefined): string {
  const normalized = normalizeText(level);
  const labels: Record<string, string> = {
    info: "信息 info",
    warning: "警告 warning",
    critical: "严重 critical"
  };
  return labels[normalized] ?? normalizeDisplay(level);
}

function normalizeFilter(value: string | null | undefined): string {
  return String(value ?? "").trim().toLowerCase();
}

function normalizeText(value: unknown): string {
  return String(value ?? "").trim();
}

function normalizeDisplay(value: unknown): string {
  const normalized = String(value ?? "").trim();
  return normalized || "-";
}

function formatOptional(value: string | number | boolean | null | undefined | object): string {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}
