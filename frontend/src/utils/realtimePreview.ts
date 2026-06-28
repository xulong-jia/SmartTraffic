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
    upload: "上传",
    rtsp: "RTSP",
    file: "本地文件",
    mock: "模拟"
  };
  return labels[sourceType] || sourceType;
}

export function buildMaskedStreamDisplay(camera: CameraRecord | null): string {
  if (!camera) {
    return "未选择摄像头";
  }
  return camera.masked_stream_url || `${formatCameraSourceLabel(camera.source_type)}源`;
}

export function buildStartDisabledReason(camera: CameraRecord | null): string {
  if (!camera) {
    return "请选择摄像头";
  }
  if (!camera.enabled) {
    return "摄像头已停用";
  }
  return "";
}

export function buildRealtimeStatusCards(status: RealtimeStatus | null) {
  return [
    { label: "状态", value: formatRealtimeStatus(status?.status || "stopped") },
    { label: "帧数", value: status?.frame_count ?? 0 },
    { label: "事件", value: status?.event_count ?? 0 },
    { label: "告警", value: status?.alert_count ?? 0 }
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
    running: "运行中",
    stopped: "已停止",
    completed: "已完成",
    pending: "待处理",
    failed: "失败",
    new: "新告警",
    acknowledged: "已确认",
    resolved: "已解决",
    ignored: "已忽略"
  };
  return labels[status || ""] ?? (status || "-");
}

function formatSeverityLabel(severity: string | null | undefined): string {
  const labels: Record<string, string> = {
    low: "低",
    medium: "中",
    high: "高"
  };
  return labels[severity || ""] ?? (severity || "-");
}

function formatAlertLevelLabel(level: string | null | undefined): string {
  const labels: Record<string, string> = {
    info: "信息",
    warning: "警告",
    critical: "严重"
  };
  return labels[level || ""] ?? (level || "-");
}
