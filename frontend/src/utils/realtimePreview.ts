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
    upload: "上传 Upload",
    rtsp: "RTSP",
    file: "本地文件 Local file",
    mock: "模拟 Mock"
  };
  return labels[sourceType] || sourceType;
}

export function buildMaskedStreamDisplay(camera: CameraRecord | null): string {
  if (!camera) {
    return "未选择摄像头 No camera selected";
  }
  return camera.masked_stream_url || `${formatCameraSourceLabel(camera.source_type)} source`;
}

export function buildStartDisabledReason(camera: CameraRecord | null): string {
  if (!camera) {
    return "请选择摄像头 Select a camera";
  }
  if (!camera.enabled) {
    return "摄像头已停用 Camera disabled";
  }
  return "";
}

export function buildRealtimeStatusCards(status: RealtimeStatus | null) {
  return [
    { label: "状态 Status", value: formatRealtimeStatus(status?.status || "stopped") },
    { label: "帧 Frames", value: status?.frame_count ?? 0 },
    { label: "事件 Events", value: status?.event_count ?? 0 },
    { label: "告警 Alerts", value: status?.alert_count ?? 0 }
  ];
}

export function buildFrameRows(frames: RealtimeFrame[]) {
  return frames.map((frame) => ({
    id: frame.id,
    frame: frame.frame_index,
    source: frame.source_label || formatCameraSourceLabel(frame.source_type),
    status: formatRealtimeStatus(frame.status),
    timestamp: frame.timestamp_ms,
    description: frame.description
  }));
}

export function buildEventRows(events: RealtimeEvent[]) {
  return events.map((event) => ({
    id: event.id,
    type: event.event_type,
    severity: formatSeverityLabel(event.severity),
    frame: event.frame_index,
    status: formatRealtimeStatus(event.status),
    description: event.description
  }));
}

export function buildAlertRows(alerts: RealtimeAlert[]) {
  return alerts.map((alert) => ({
    id: alert.id,
    level: formatAlertLevelLabel(alert.level),
    type: alert.event_type,
    status: formatRealtimeStatus(alert.status),
    message: alert.message
  }));
}

function formatRealtimeStatus(status: string | null | undefined): string {
  const labels: Record<string, string> = {
    running: "运行中 running",
    stopped: "已停止 stopped",
    completed: "已完成 completed",
    pending: "待处理 pending",
    failed: "失败 failed",
    new: "新告警 new",
    acknowledged: "已确认 acknowledged",
    resolved: "已解决 resolved",
    ignored: "已忽略 ignored"
  };
  return labels[status || ""] ?? (status || "-");
}

function formatSeverityLabel(severity: string | null | undefined): string {
  const labels: Record<string, string> = {
    low: "低 low",
    medium: "中 medium",
    high: "高 high"
  };
  return labels[severity || ""] ?? (severity || "-");
}

function formatAlertLevelLabel(level: string | null | undefined): string {
  const labels: Record<string, string> = {
    info: "信息 info",
    warning: "警告 warning",
    critical: "严重 critical"
  };
  return labels[level || ""] ?? (level || "-");
}
