import type {
  AnalysisRunDetections,
  AnalysisRunTracks,
  EventRecord,
  EventsResponse,
  TrajectoryPointsResponse,
  ZoneRecord
} from "../types";
import { getEventId } from "./eventTimeline";
import { normalizeBbox, selectedTrackIdFromEvent, selectedZoneIdFromEvent } from "./videoOverlay";

export interface OverlayDataBundle {
  detections: AnalysisRunDetections["frames"];
  tracks: AnalysisRunTracks["frames"];
  trajectoryFrames: TrajectoryPointsResponse["frames"];
  events: EventRecord[];
  zones: ZoneRecord[];
  selectedEvent: EventRecord | null;
  selectedTrackId: number | null;
  selectedZoneId: string | null;
}

export function buildOverlayDataBundle(input: {
  detections?: AnalysisRunDetections | null;
  tracks?: AnalysisRunTracks | null;
  trajectory?: TrajectoryPointsResponse | null;
  events?: EventsResponse | null;
  zones?: ZoneRecord[] | null;
  selectedEventId?: string | null;
}): OverlayDataBundle {
  const events = input.events?.events ?? [];
  const selectedEvent = findSelectedEvent(events, input.selectedEventId ?? null);
  return {
    detections: input.detections?.frames ?? [],
    tracks: input.tracks?.frames ?? [],
    trajectoryFrames: input.trajectory?.frames ?? [],
    events,
    zones: input.zones ?? [],
    selectedEvent,
    selectedTrackId: selectedTrackIdFromEvent(selectedEvent),
    selectedZoneId: selectedZoneIdFromEvent(selectedEvent)
  };
}

export function findSelectedEvent(
  events: EventRecord[],
  selectedEventId: string | null
): EventRecord | null {
  if (!selectedEventId) {
    return null;
  }
  return events.find((event, index) => getEventId(event, index) === selectedEventId) ?? null;
}

export function inferOverlaySize(input: {
  detections?: AnalysisRunDetections | null;
  tracks?: AnalysisRunTracks | null;
  zones?: ZoneRecord[] | null;
}): { width: number; height: number } {
  const detectionBoxes =
    input.detections?.frames.flatMap((frame) =>
      frame.detections
        .map((item) => normalizeBbox(item.bbox ?? item))
        .filter((box): box is [number, number, number, number] => box !== null)
    ) ?? [];
  const trackBoxes =
    input.tracks?.frames.flatMap((frame) =>
      frame.tracks
        .map((item) => normalizeBbox(item.bbox ?? item.metadata ?? item))
        .filter((box): box is [number, number, number, number] => box !== null)
    ) ?? [];
  const zonePoints = input.zones?.flatMap((zone) => zone.polygon) ?? [];
  const boxes = [...detectionBoxes, ...trackBoxes];
  const maxX = Math.max(
    960,
    ...boxes.map((box) => Number(box[0])),
    ...boxes.map((box) => Number(box[2])),
    ...zonePoints.map((point) => Number(point[0] ?? 0))
  );
  const maxY = Math.max(
    540,
    ...boxes.map((box) => Number(box[1])),
    ...boxes.map((box) => Number(box[3])),
    ...zonePoints.map((point) => Number(point[1] ?? 0))
  );
  return { width: maxX, height: maxY };
}
