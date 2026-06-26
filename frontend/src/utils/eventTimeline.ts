import type { EventRecord } from "../types";

export interface EventTimelineFilters {
  eventType?: string;
  severity?: string;
  status?: string;
}

export function getEventId(event: EventRecord, fallbackIndex = 0): string {
  if (typeof event.event_id === "string" && event.event_id) {
    return event.event_id;
  }
  if (typeof event.id === "string" && event.id) {
    return event.id;
  }
  return `event_${fallbackIndex}`;
}

export function getEventSeekTimeMs(event: EventRecord): number {
  if (Number.isFinite(event.start_time_ms)) {
    return Number(event.start_time_ms);
  }
  if (Number.isFinite(event.timestamp_ms)) {
    return Number(event.timestamp_ms);
  }
  if (Number.isFinite(event.start_frame)) {
    return Number(event.start_frame) * (1000 / 30);
  }
  if (Number.isFinite(event.frame_index)) {
    return Number(event.frame_index) * (1000 / 30);
  }
  return 0;
}

export function sortEventsByTime(events: EventRecord[]): EventRecord[] {
  return [...events].sort((left, right) => getEventSeekTimeMs(left) - getEventSeekTimeMs(right));
}

export function filterEvents(
  events: EventRecord[],
  filters: EventTimelineFilters
): EventRecord[] {
  return sortEventsByTime(events).filter((event) => {
    if (filters.eventType && event.event_type !== filters.eventType) {
      return false;
    }
    if (filters.severity && event.severity !== filters.severity) {
      return false;
    }
    if (filters.status && event.status !== filters.status) {
      return false;
    }
    return true;
  });
}

export function isSelectedEvent(
  event: EventRecord,
  selectedEventId: string | null,
  fallbackIndex = 0
): boolean {
  return selectedEventId !== null && getEventId(event, fallbackIndex) === selectedEventId;
}

export function uniqueEventValues(
  events: EventRecord[],
  field: "event_type" | "severity" | "status"
): string[] {
  return Array.from(
    new Set(
      events
        .map((event) => event[field])
        .filter((value): value is string => typeof value === "string" && value.length > 0)
    )
  ).sort();
}
