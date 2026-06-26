import type { EventRulePayload, EventRuleRecord, EventRuleUpdatePayload } from "../types";

export const EVENT_TYPES = [
  "wrong_way_driving",
  "illegal_parking",
  "danger_zone_intrusion",
  "pedestrian_in_vehicle_lane",
  "congestion",
  "flow_counting"
] as const;

export interface EventRuleFormState {
  id: string | null;
  name: string;
  eventType: string;
  enabled: boolean;
  zoneId: string;
  targetClassesText: string;
  parametersText: string;
  cooldownSeconds: number;
  severity: string;
  version: number;
  minTrackLength: number;
}

export interface PayloadBuildResult<T> {
  payload: T | null;
  errors: string[];
}

export function createEmptyEventRuleFormState(): EventRuleFormState {
  return {
    id: null,
    name: "",
    eventType: "wrong_way_driving",
    enabled: true,
    zoneId: "",
    targetClassesText: "car,bus,truck,motorcycle,bicycle",
    parametersText: "{}",
    cooldownSeconds: 0,
    severity: "medium",
    version: 1,
    minTrackLength: 1
  };
}

export function eventRuleToFormState(rule: EventRuleRecord): EventRuleFormState {
  return {
    id: rule.id,
    name: rule.name,
    eventType: rule.event_type,
    enabled: rule.enabled,
    zoneId: rule.zone_id ?? "",
    targetClassesText: rule.target_classes.join(","),
    parametersText: JSON.stringify(rule.parameters ?? {}, null, 2),
    cooldownSeconds: Number(rule.cooldown_seconds ?? 0),
    severity: rule.severity || "medium",
    version: Number(rule.version ?? 1),
    minTrackLength: Number(rule.min_track_length ?? 1)
  };
}

export function buildEventRulePayload(
  state: EventRuleFormState
): PayloadBuildResult<EventRulePayload> {
  const base = buildEventRuleBase(state);
  if (base.errors.length > 0 || base.payload === null) {
    return base;
  }
  return { payload: base.payload, errors: [] };
}

export function buildEventRulePatchPayload(
  state: EventRuleFormState
): PayloadBuildResult<EventRuleUpdatePayload> {
  const base = buildEventRuleBase(state);
  if (base.errors.length > 0 || base.payload === null) {
    return { payload: null, errors: base.errors };
  }
  return { payload: base.payload, errors: [] };
}

export function parseTargetClasses(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function buildEventRuleBase(
  state: EventRuleFormState
): PayloadBuildResult<EventRulePayload> {
  const errors: string[] = [];
  if (!state.name.trim()) {
    errors.push("Rule name is required.");
  }
  if (!EVENT_TYPES.includes(state.eventType as (typeof EVENT_TYPES)[number])) {
    errors.push("Event type is unsupported.");
  }
  if (!Number.isFinite(state.cooldownSeconds) || state.cooldownSeconds < 0) {
    errors.push("Cooldown seconds must be non-negative.");
  }
  if (!Number.isFinite(state.version) || state.version < 1) {
    errors.push("Rule version must be at least 1.");
  }
  if (!Number.isFinite(state.minTrackLength) || state.minTrackLength < 1) {
    errors.push("Minimum track length must be at least 1.");
  }

  let parameters: Record<string, unknown> = {};
  try {
    const parsed = JSON.parse(state.parametersText || "{}") as unknown;
    if (parsed === null || Array.isArray(parsed) || typeof parsed !== "object") {
      errors.push("Parameters JSON must be an object.");
    } else {
      parameters = parsed as Record<string, unknown>;
    }
  } catch {
    errors.push("Parameters JSON is invalid.");
  }

  if (errors.length > 0) {
    return { payload: null, errors };
  }

  return {
    payload: {
      name: state.name.trim(),
      event_type: state.eventType,
      enabled: state.enabled,
      zone_id: state.zoneId.trim() || null,
      target_classes: parseTargetClasses(state.targetClassesText),
      parameters,
      cooldown_seconds: Number(state.cooldownSeconds),
      severity: state.severity.trim() || "medium",
      version: Math.max(1, Math.trunc(state.version || 1)),
      min_track_length: Math.max(1, Math.trunc(state.minTrackLength || 1))
    },
    errors: []
  };
}
