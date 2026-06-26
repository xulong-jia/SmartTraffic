import { apiDelete, apiGet, apiPatch, apiPost } from "./client";
import type { EventRulePayload, EventRuleRecord, EventRuleUpdatePayload } from "../types";

export function listEventRules(
  params: { eventType?: string; enabled?: boolean; zoneId?: string } = {}
): Promise<EventRuleRecord[]> {
  const query = new URLSearchParams();
  if (params.eventType) {
    query.set("event_type", params.eventType);
  }
  if (params.enabled !== undefined) {
    query.set("enabled", String(params.enabled));
  }
  if (params.zoneId) {
    query.set("zone_id", params.zoneId);
  }
  const serialized = query.toString();
  return apiGet<EventRuleRecord[]>(
    serialized ? `/api/event-rules?${serialized}` : "/api/event-rules"
  );
}

export function createEventRule(payload: EventRulePayload): Promise<EventRuleRecord> {
  return apiPost<EventRuleRecord>("/api/event-rules", JSON.stringify(payload));
}

export function updateEventRule(
  ruleId: string,
  payload: EventRuleUpdatePayload
): Promise<EventRuleRecord> {
  return apiPatch<EventRuleRecord>(`/api/event-rules/${encodeURIComponent(ruleId)}`, payload);
}

export function deleteEventRule(ruleId: string): Promise<{ id: string; deleted: boolean }> {
  return apiDelete<{ id: string; deleted: boolean }>(
    `/api/event-rules/${encodeURIComponent(ruleId)}`
  );
}
