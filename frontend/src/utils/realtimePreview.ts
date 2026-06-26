import type {
  CameraRecord,
  CameraSourceType,
  RealtimeAlert,
  RealtimeEvent,
  RealtimeFrame,
  RealtimeStatus
} from "../types";

export function formatCameraSourceLabel(sourceType: CameraSourceType | string): string {
  const labels: Record<string, string> = {
    upload: "Upload",
    rtsp: "RTSP",
    file: "Local file",
    mock: "Mock"
  };
  return labels[sourceType] || sourceType;
}

export function buildMaskedStreamDisplay(camera: CameraRecord | null): string {
  if (!camera) {
    return "No camera selected";
  }
  return camera.masked_stream_url || `${formatCameraSourceLabel(camera.source_type)} source`;
}

export function buildStartDisabledReason(camera: CameraRecord | null): string {
  if (!camera) {
    return "Select a camera";
  }
  if (!camera.enabled) {
    return "Camera disabled";
  }
  return "";
}

export function buildRealtimeStatusCards(status: RealtimeStatus | null) {
  return [
    { label: "Status", value: status?.status || "stopped" },
    { label: "Frames", value: status?.frame_count ?? 0 },
    { label: "Events", value: status?.event_count ?? 0 },
    { label: "Alerts", value: status?.alert_count ?? 0 }
  ];
}

export function buildFrameRows(frames: RealtimeFrame[]) {
  return frames.map((frame) => ({
    id: frame.id,
    frame: frame.frame_index,
    source: frame.source_label || formatCameraSourceLabel(frame.source_type),
    status: frame.status,
    timestamp: frame.timestamp_ms,
    description: frame.description
  }));
}

export function buildEventRows(events: RealtimeEvent[]) {
  return events.map((event) => ({
    id: event.id,
    type: event.event_type,
    severity: event.severity,
    frame: event.frame_index,
    status: event.status,
    description: event.description
  }));
}

export function buildAlertRows(alerts: RealtimeAlert[]) {
  return alerts.map((alert) => ({
    id: alert.id,
    level: alert.level,
    type: alert.event_type,
    status: alert.status,
    message: alert.message
  }));
}
