import type { CountingLineConfig, DirectionConfig, ZonePayload, ZoneRecord } from "../types";
import {
  type EditorLine,
  type EditorPoint,
  fromApiPoint,
  fromApiPolygon,
  isCompleteLine,
  isValidPolygon,
  setLinePoint,
  toApiPoint,
  toApiPolygon
} from "./zoneEditorGeometry";

export const ZONE_TYPES = [
  "vehicle_lane",
  "pedestrian_area",
  "no_parking_zone",
  "danger_zone",
  "counting_zone",
  "roi"
] as const;

export const DRAWING_MODES = ["polygon", "direction", "counting"] as const;

export type ZoneType = (typeof ZONE_TYPES)[number];
export type DrawingMode = (typeof DRAWING_MODES)[number];

export interface ZoneEditorState {
  id: string | null;
  name: string;
  zoneType: ZoneType;
  polygon: EditorPoint[];
  directionLine: EditorLine;
  allowedAngle: number;
  reverseAngleThreshold: number;
  countingLine: EditorLine;
  inDirection: "any" | "positive" | "negative";
  enabled: boolean;
  version: number;
  videoId: string;
  cameraId: string;
}

export interface ZoneValidationResult {
  valid: boolean;
  errors: string[];
}

export function createEmptyZoneEditorState(): ZoneEditorState {
  return {
    id: null,
    name: "",
    zoneType: "vehicle_lane",
    polygon: [],
    directionLine: { start: null, end: null },
    allowedAngle: 0,
    reverseAngleThreshold: 135,
    countingLine: { start: null, end: null },
    inDirection: "any",
    enabled: true,
    version: 1,
    videoId: "",
    cameraId: ""
  };
}

export function zoneToEditorState(zone: ZoneRecord): ZoneEditorState {
  return {
    ...createEmptyZoneEditorState(),
    id: zone.id,
    name: zone.name,
    zoneType: normalizeZoneType(zone.zone_type),
    polygon: fromApiPolygon(zone.polygon),
    directionLine: {
      start: fromApiPoint(zone.direction?.start_point),
      end: fromApiPoint(zone.direction?.end_point)
    },
    allowedAngle: numberOrDefault(zone.direction?.allowed_angle, 0),
    reverseAngleThreshold: numberOrDefault(zone.direction?.reverse_angle_threshold, 135),
    countingLine: {
      start: fromApiPoint(zone.counting_line?.start_point),
      end: fromApiPoint(zone.counting_line?.end_point)
    },
    inDirection: normalizeDirection(zone.counting_line?.in_direction),
    enabled: zone.enabled,
    videoId: zone.video_id ?? "",
    cameraId: zone.camera_id ?? "",
    version: Number.isFinite(zone.version) ? Number(zone.version) : 1
  };
}

export function addPointForMode(
  state: ZoneEditorState,
  mode: DrawingMode,
  point: EditorPoint
): ZoneEditorState {
  if (mode === "polygon") {
    return { ...state, polygon: [...state.polygon, point] };
  }
  if (mode === "direction") {
    return { ...state, directionLine: setLinePoint(state.directionLine, point) };
  }
  return { ...state, countingLine: setLinePoint(state.countingLine, point) };
}

export function clearDrawingForMode(state: ZoneEditorState, mode: DrawingMode): ZoneEditorState {
  if (mode === "polygon") {
    return { ...state, polygon: [] };
  }
  if (mode === "direction") {
    return { ...state, directionLine: { start: null, end: null } };
  }
  return { ...state, countingLine: { start: null, end: null } };
}

export function validateZoneEditorState(
  state: ZoneEditorState,
  mode: DrawingMode = "polygon"
): ZoneValidationResult {
  const errors: string[] = [];
  if (!state.name.trim()) {
    errors.push("Zone name is required.");
  }
  if (!state.zoneType) {
    errors.push("Zone type is required.");
  }
  if (!isValidPolygon(state.polygon)) {
    errors.push("Polygon requires at least three points.");
  }
  if (mode === "direction" && !isCompleteLine(state.directionLine)) {
    errors.push("Direction line requires two points.");
  }
  if (mode === "counting" && !isCompleteLine(state.countingLine)) {
    errors.push("Counting line requires two points.");
  }
  if (state.directionLine.start !== null || state.directionLine.end !== null) {
    if (!isCompleteLine(state.directionLine)) {
      errors.push("Direction line is incomplete.");
    }
  }
  if (state.countingLine.start !== null || state.countingLine.end !== null) {
    if (!isCompleteLine(state.countingLine)) {
      errors.push("Counting line is incomplete.");
    }
  }
  if (!Number.isFinite(state.version) || state.version < 1) {
    errors.push("Version must be at least 1.");
  }
  return { valid: errors.length === 0, errors };
}

export function buildZonePayload(state: ZoneEditorState): ZonePayload {
  return {
    name: state.name.trim(),
    zone_type: state.zoneType,
    polygon: toApiPolygon(state.polygon),
    direction: buildDirectionConfig(state),
    counting_line: buildCountingLineConfig(state),
    enabled: state.enabled,
    video_id: optionalString(state.videoId),
    camera_id: optionalString(state.cameraId),
    version: Math.max(1, Math.trunc(state.version || 1))
  };
}

export function buildZonePatchPayload(state: ZoneEditorState): Partial<ZonePayload> {
  return buildZonePayload(state);
}

function buildDirectionConfig(state: ZoneEditorState): DirectionConfig | null {
  if (!isCompleteLine(state.directionLine) || !state.directionLine.start || !state.directionLine.end) {
    return null;
  }
  return {
    start_point: toApiPoint(state.directionLine.start),
    end_point: toApiPoint(state.directionLine.end),
    allowed_angle: Number(state.allowedAngle),
    reverse_angle_threshold: Number(state.reverseAngleThreshold)
  };
}

function buildCountingLineConfig(state: ZoneEditorState): CountingLineConfig | null {
  if (!isCompleteLine(state.countingLine) || !state.countingLine.start || !state.countingLine.end) {
    return null;
  }
  return {
    start_point: toApiPoint(state.countingLine.start),
    end_point: toApiPoint(state.countingLine.end),
    in_direction: state.inDirection,
    enabled: true
  };
}

function normalizeZoneType(value: string): ZoneType {
  return ZONE_TYPES.includes(value as ZoneType) ? (value as ZoneType) : "roi";
}

function normalizeDirection(value: string | undefined): "any" | "positive" | "negative" {
  if (value === "positive" || value === "negative") {
    return value;
  }
  return "any";
}

function numberOrDefault(value: number | null | undefined, fallback: number): number {
  return Number.isFinite(value) ? Number(value) : fallback;
}

function optionalString(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}
