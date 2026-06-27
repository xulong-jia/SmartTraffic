import type { EventRecord } from "../types";

export interface EventTableFilters {
  status?: string | null;
  eventType?: string | null;
  severity?: string | null;
}

export interface EventTableRow {
  id: string;
  eventType: string;
  severity: string;
  status: string;
  trackId: string;
  zoneId: string;
  startTimeMs: string;
  runId: string;
  selected: boolean;
}

export function sortEventTableRows(events: EventRecord[]): EventRecord[] {
  return [...events].sort((left, right) => {
    const leftTime = numericTime(left);
    const rightTime = numericTime(right);
    if (leftTime !== rightTime) {
      return leftTime - rightTime;
    }
    return eventId(left).localeCompare(eventId(right));
  });
}

export function filterEventTableRows(
  events: EventRecord[],
  filters: EventTableFilters = {}
): EventRecord[] {
  const status = normalizeFilter(filters.status);
  const eventType = normalizeFilter(filters.eventType);
  const severity = normalizeFilter(filters.severity);
  return events.filter((event) => {
    if (status && normalizeFilter(event.status) !== status) {
      return false;
    }
    if (eventType && normalizeFilter(event.event_type) !== eventType) {
      return false;
    }
    if (severity && normalizeFilter(event.severity) !== severity) {
      return false;
    }
    return true;
  });
}

export function buildEventTableRows(
  events: EventRecord[],
  selectedEventId: string | null = null
): EventTableRow[] {
  return sortEventTableRows(events).map((event, index) => {
    const id = eventId(event) || `event-${index}`;
    return {
      id,
      eventType: formatOptional(event.event_type),
      severity: formatOptional(event.severity),
      status: formatEventStatusLabel(event.status),
      trackId: formatOptional(event.track_id),
      zoneId: formatOptional(event.zone_id),
      startTimeMs: formatOptional(event.start_time_ms ?? event.timestamp_ms ?? event.start_frame),
      runId: formatOptional(event.run_id),
      selected: id === selectedEventId
    };
  });
}

export function eventTableEmptyLabel(
  loading: boolean,
  error: string,
  events: EventRecord[]
): string {
  if (loading) {
    return "正在加载事件...";
  }
  if (error) {
    return error;
  }
  if (events.length === 0) {
    return "暂无事件。请先运行一次视频分析。";
  }
  return "";
}

function formatEventStatusLabel(status: string | number | boolean | null | undefined | object): string {
  const raw = formatOptional(status);
  const labels: Record<string, string> = {
    pending: "待处理 pending",
    confirmed: "已确认 confirmed",
    new: "新事件 new",
    resolved: "已解决 resolved",
    ignored: "已忽略 ignored"
  };
  return labels[raw] ?? raw;
}

export function getEventTableId(event: EventRecord, index = 0): string {
  return eventId(event) || `event-${index}`;
}

function numericTime(event: EventRecord): number {
  const value = event.start_time_ms ?? event.timestamp_ms ?? event.start_frame ?? Number.MAX_SAFE_INTEGER;
  return typeof value === "number" ? value : Number.MAX_SAFE_INTEGER;
}

function eventId(event: EventRecord): string {
  return String(event.event_id ?? event.id ?? "").trim();
}

function normalizeFilter(value: string | number | boolean | null | undefined | object): string {
  return String(value ?? "").trim().toLowerCase();
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
