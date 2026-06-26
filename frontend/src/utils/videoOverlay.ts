import type {
  EventRecord,
  FrameDetectionResult,
  FrameTrackingResult,
  TrajectoryFrame,
  TrajectoryPoint,
  ZoneRecord
} from "../types";

export interface Point2D {
  x: number;
  y: number;
}

export interface Box2D {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface AspectFit {
  scale: number;
  offsetX: number;
  offsetY: number;
  renderedWidth: number;
  renderedHeight: number;
}

export interface OverlayDetection {
  bbox: number[];
  class_name: string;
  confidence?: number | null;
}

export interface OverlayTrack {
  track_id: number;
  bbox: number[];
  class_name?: string;
  confidence?: number | null;
  state?: string;
}

export interface TrackPolyline {
  trackId: number;
  points: Point2D[];
  highlighted: boolean;
}

const DEFAULT_FRAME_DURATION_MS = 1000 / 30;

export function computeAspectFit(
  sourceWidth: number,
  sourceHeight: number,
  containerWidth: number,
  containerHeight: number
): AspectFit {
  const safeSourceWidth = positiveOrDefault(sourceWidth, 960);
  const safeSourceHeight = positiveOrDefault(sourceHeight, 540);
  const safeContainerWidth = positiveOrDefault(containerWidth, safeSourceWidth);
  const safeContainerHeight = positiveOrDefault(containerHeight, safeSourceHeight);
  const scale = Math.min(
    safeContainerWidth / safeSourceWidth,
    safeContainerHeight / safeSourceHeight
  );
  const renderedWidth = safeSourceWidth * scale;
  const renderedHeight = safeSourceHeight * scale;
  return {
    scale,
    offsetX: (safeContainerWidth - renderedWidth) / 2,
    offsetY: (safeContainerHeight - renderedHeight) / 2,
    renderedWidth,
    renderedHeight
  };
}

export function scalePoint(point: number[], fit: AspectFit): Point2D {
  return {
    x: Number(point[0] ?? 0) * fit.scale + fit.offsetX,
    y: Number(point[1] ?? 0) * fit.scale + fit.offsetY
  };
}

export function scaleBox(box: number[], fit: AspectFit): Box2D {
  const [x1, y1, x2, y2] = normalizeBox(box);
  const start = scalePoint([x1, y1], fit);
  const end = scalePoint([x2, y2], fit);
  return {
    x: start.x,
    y: start.y,
    width: Math.max(0, end.x - start.x),
    height: Math.max(0, end.y - start.y)
  };
}

export function clampBox(box: number[], width: number, height: number): number[] {
  const [x1, y1, x2, y2] = normalizeBox(box);
  return [
    clamp(x1, 0, width),
    clamp(y1, 0, height),
    clamp(x2, 0, width),
    clamp(y2, 0, height)
  ];
}

export function formatConfidence(value: number | null | undefined): string {
  if (!Number.isFinite(value)) {
    return "";
  }
  return `${Math.round(Number(value) * 100)}%`;
}

export function frameTimeMs(frame: { timestamp_ms?: number | null; frame_index?: number }): number {
  if (Number.isFinite(frame.timestamp_ms)) {
    return Number(frame.timestamp_ms);
  }
  return Number(frame.frame_index ?? 0) * DEFAULT_FRAME_DURATION_MS;
}

export function findNearestFrame<T extends { timestamp_ms?: number | null; frame_index?: number }>(
  frames: T[],
  currentTimeMs: number
): T | null {
  if (frames.length === 0) {
    return null;
  }
  return frames.reduce((best, frame) => {
    const bestDelta = Math.abs(frameTimeMs(best) - currentTimeMs);
    const frameDelta = Math.abs(frameTimeMs(frame) - currentTimeMs);
    return frameDelta < bestDelta ? frame : best;
  }, frames[0]);
}

export function filterDetectionsForTime(
  frames: FrameDetectionResult[],
  currentTimeMs: number
): OverlayDetection[] {
  return findNearestFrame(frames, currentTimeMs)?.detections ?? [];
}

export function filterTracksForTime(
  frames: FrameTrackingResult[],
  currentTimeMs: number
): OverlayTrack[] {
  return findNearestFrame(frames, currentTimeMs)?.tracks ?? [];
}

export function groupTrajectoryPolylines(
  frames: TrajectoryFrame[],
  currentTimeMs: number,
  selectedTrackId: number | null
): TrackPolyline[] {
  const maxTime = currentTimeMs + DEFAULT_FRAME_DURATION_MS;
  const grouped = new Map<number, Point2D[]>();
  frames
    .filter((frame) => frameTimeMs(frame) <= maxTime)
    .forEach((frame) => {
      frame.trajectory_points.forEach((point) => {
        const trackId = point.track_id;
        const center = getTrajectoryPointCenter(point);
        if (trackId === undefined || trackId === null || center === null) {
          return;
        }
        const points = grouped.get(trackId) ?? [];
        points.push(center);
        grouped.set(trackId, points);
      });
    });
  return Array.from(grouped.entries()).map(([trackId, points]) => ({
    trackId,
    points,
    highlighted: selectedTrackId !== null && trackId === selectedTrackId
  }));
}

export function zonePolygonPoints(zone: ZoneRecord): Point2D[] {
  return zone.polygon
    .filter((point) => Array.isArray(point) && point.length === 2)
    .map((point) => ({ x: Number(point[0]), y: Number(point[1]) }));
}

export function selectedTrackIdFromEvent(event: EventRecord | null | undefined): number | null {
  return Number.isFinite(event?.track_id) ? Number(event?.track_id) : null;
}

export function selectedZoneIdFromEvent(event: EventRecord | null | undefined): string | null {
  return typeof event?.zone_id === "string" && event.zone_id ? event.zone_id : null;
}

export function isTrackHighlighted(trackId: number | null | undefined, selectedTrackId: number | null): boolean {
  return selectedTrackId !== null && Number(trackId) === selectedTrackId;
}

export function isZoneHighlighted(zoneId: string | null | undefined, selectedZoneId: string | null): boolean {
  return selectedZoneId !== null && zoneId === selectedZoneId;
}

function getTrajectoryPointCenter(point: TrajectoryPoint): Point2D | null {
  const center = point.center ?? point.bottom_center;
  if (!Array.isArray(center) || center.length !== 2) {
    return null;
  }
  return { x: Number(center[0]), y: Number(center[1]) };
}

function normalizeBox(box: number[]): number[] {
  const x1 = Number(box[0] ?? 0);
  const y1 = Number(box[1] ?? 0);
  const x2 = Number(box[2] ?? x1);
  const y2 = Number(box[3] ?? y1);
  return [Math.min(x1, x2), Math.min(y1, y2), Math.max(x1, x2), Math.max(y1, y2)];
}

function positiveOrDefault(value: number, fallback: number): number {
  return Number.isFinite(value) && value > 0 ? value : fallback;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}
