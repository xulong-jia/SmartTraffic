export interface ReviewQuery {
  run_id?: string;
  event_id?: string;
  alert_id?: string;
  status?: string;
  event_type?: string;
}

export interface ReviewFilterState {
  runId?: string;
  status?: string;
  eventType?: string;
  eventId?: string;
  alertId?: string;
}

export function buildReviewLink(
  runId?: string | null,
  eventId?: string | null,
  alertId?: string | null,
  filters: { status?: string | null; event_type?: string | null } = {}
): string {
  const query = new URLSearchParams();
  appendQueryValue(query, "run_id", runId);
  appendQueryValue(query, "event_id", eventId);
  appendQueryValue(query, "alert_id", alertId);
  appendQueryValue(query, "status", filters.status);
  appendQueryValue(query, "event_type", filters.event_type);
  const serialized = query.toString();
  return serialized ? `/review?${serialized}` : "/review";
}

export function parseReviewQuery(search: string): ReviewQuery {
  const query = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
  const parsed: ReviewQuery = {};
  copyQueryValue(query, parsed, "run_id");
  copyQueryValue(query, parsed, "event_id");
  copyQueryValue(query, parsed, "alert_id");
  copyQueryValue(query, parsed, "status");
  copyQueryValue(query, parsed, "event_type");
  return parsed;
}

export function normalizeReviewFiltersFromQuery(query: ReviewQuery): ReviewFilterState {
  const normalized: ReviewFilterState = {};
  if (query.run_id) {
    normalized.runId = query.run_id;
  }
  if (query.status) {
    normalized.status = query.status;
  }
  if (query.event_type) {
    normalized.eventType = query.event_type;
  }
  if (query.event_id) {
    normalized.eventId = query.event_id;
  }
  if (query.alert_id) {
    normalized.alertId = query.alert_id;
  }
  return normalized;
}

function appendQueryValue(
  query: URLSearchParams,
  key: string,
  value: string | null | undefined
) {
  const trimmed = value?.trim();
  if (trimmed) {
    query.set(key, trimmed);
  }
}

function copyQueryValue(query: URLSearchParams, target: ReviewQuery, key: keyof ReviewQuery) {
  const value = query.get(key)?.trim();
  if (value) {
    target[key] = value;
  }
}
