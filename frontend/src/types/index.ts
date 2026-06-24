export interface VideoRecord {
  id: string;
  filename: string;
  status: string;
  fps: number;
  width: number;
  height: number;
  duration_seconds: number;
  total_frames: number;
}

export interface ProcessingTask {
  id: string;
  video_id: string;
  run_id: string;
  status: string;
  progress: number;
}

export interface ArtifactAvailability {
  available?: boolean;
  path?: string;
  status: string;
  schema_version?: string | null;
  error?: string;
}

export type ArtifactStatus = ArtifactAvailability;
export type MetadataSummary = ArtifactAvailability;
export type ManifestSummary = ArtifactAvailability;
export type ArtifactIndexSummary = ArtifactAvailability;

export interface ArtifactSummaryItem {
  status: string;
  path: string;
  record_count: number;
  [key: string]: string | number | boolean | null | undefined;
}

export type ArtifactSummary = Record<string, ArtifactSummaryItem>;

export interface AnalysisRunSummary {
  id: string;
  run_id?: string;
  video_id?: string;
  status: string;
  mode?: string;
  result_dir?: string;
  source?: string;
  schema_version?: string;
  created_at?: string;
  updated_at?: string;
  started_at?: string;
  finished_at?: string;
  metadata?: MetadataSummary;
  manifest?: ManifestSummary;
  artifact_index?: ArtifactIndexSummary;
  artifact_paths?: Record<string, string>;
  artifact_summary?: ArtifactSummary;
}

export type AnalysisRun = AnalysisRunSummary;

export interface AnalysisRunListParams {
  status?: string;
  video_id?: string;
  limit?: number;
  offset?: number;
}

export interface AnalysisRunListResponse {
  items: AnalysisRunSummary[];
  total: number;
  limit: number;
  offset: number;
}

export type AnalysisRunsListResponse = AnalysisRunListResponse;

export interface DetectionProcessOptions {
  mode?: "detection_only" | "detection_tracking" | "detection_tracking_trajectory";
  dry_run?: boolean;
  detector_dry_run?: boolean;
  tracker_dry_run?: boolean;
  frame_stride?: number;
  max_frames?: number;
  conf_threshold?: number;
  iou_threshold?: number;
  write_preview?: boolean;
  direction_window?: number;
  dwell_speed_threshold?: number;
  max_history_points?: number | null;
}

export interface DetectionProcessResult {
  run_id: string;
  video_id: string;
  status: string;
  stage: string;
  next_stage: string;
  total_frames_processed: number;
  total_detections: number;
  total_tracks?: number | null;
  unique_track_ids?: number | null;
  total_trajectory_points?: number | null;
  per_class_counts: Record<string, number>;
  per_class_track_counts?: Record<string, number> | null;
  track_state_counts?: Record<string, number> | null;
  trajectory_track_state_counts?: Record<string, number> | null;
  avg_track_length?: number | null;
  max_track_length?: number | null;
  avg_speed_px_per_second?: number | null;
  artifacts: Record<string, string>;
}

export interface DetectionSummary {
  total_frames_processed: number;
  total_detections: number;
  per_class_counts: Record<string, number>;
}

export interface FrameDetectionResult {
  frame_index: number;
  timestamp_ms?: number | null;
  detections: Array<{
    class_id?: number | null;
    class_name: string;
    confidence: number;
    bbox: number[];
  }>;
}

export interface AnalysisRunDetections {
  run_id: string;
  video_id: string;
  summary: DetectionSummary;
  frames: FrameDetectionResult[];
  rows: Array<Record<string, string>>;
  limit: number;
}

export interface TrackingSummary {
  total_frames_processed: number;
  total_tracks: number;
  unique_track_ids: number;
  per_class_track_counts: Record<string, number>;
  track_state_counts: Record<string, number>;
}

export interface FrameTrackingResult {
  frame_index: number;
  timestamp_ms?: number | null;
  tracks: Array<{
    track_id: number;
    class_id?: number | null;
    class_name: string;
    confidence: number;
    bbox: number[];
    center: number[];
    state: string;
  }>;
}

export interface AnalysisRunTracks {
  run_id: string;
  video_id: string;
  summary: TrackingSummary;
  frames: FrameTrackingResult[];
  rows: Array<Record<string, string>>;
  limit: number;
}

export interface TrajectorySummary {
  run_id?: string;
  video_id?: string;
  total_frames_processed?: number;
  total_trajectory_points?: number;
  unique_track_ids?: number;
  per_class_track_counts?: Record<string, number>;
  track_state_counts?: Record<string, number>;
  avg_track_length?: number;
  max_track_length?: number;
  speed_unit?: string;
  avg_speed_px_per_second?: number | null;
  zone_counts?: Record<string, number>;
  line_crossing_counts?: Record<string, number>;
  [key: string]: unknown;
}

export interface TrajectoryPoint {
  track_id?: number;
  class_id?: number | null;
  class_name?: string;
  confidence?: number;
  bbox?: number[];
  center?: number[];
  bottom_center?: number[];
  state?: string;
  speed_px_per_frame?: number | null;
  speed_px_per_second?: number | null;
  direction_vector?: number[] | null;
  moving_angle?: number | null;
  dwell_time_ms?: number;
  zone_ids?: string[];
  zone_history?: unknown[];
  lane_relation?: Record<string, unknown>;
  line_crossings?: unknown[];
  track_length?: number;
  last_seen_frame?: number;
  last_seen_timestamp_ms?: number | null;
}

export interface TrajectoryFrame {
  run_id?: string;
  video_id?: string;
  frame_index?: number;
  timestamp_ms?: number | null;
  trajectory_points: TrajectoryPoint[];
}

export type TrajectoryPointRow = Record<string, string | number | null | undefined>;

export interface TrajectoryPointsResponse {
  run_id: string;
  video_id?: string;
  summary: TrajectorySummary;
  frames: TrajectoryFrame[];
  rows: TrajectoryPointRow[];
  limit: number;
  track_id?: number | null;
}

export interface EventSummary {
  total_events?: number;
  per_event_type_counts?: Record<string, number>;
  per_severity_counts?: Record<string, number>;
  per_status_counts?: Record<string, number>;
  unique_track_ids?: number;
  rule_execution_counts?: Record<string, number>;
  first_event_time_ms?: number | null;
  last_event_time_ms?: number | null;
  [key: string]: unknown;
}

export interface TrafficEvent {
  [key: string]: string | number | boolean | null | object | undefined;
  event_id?: string;
  event_type?: string | null;
  track_id?: number | null;
  zone_id?: string | null;
  start_frame?: number | null;
  end_frame?: number | null;
  severity?: string | null;
  status?: string | null;
}

export type EventRecord = TrafficEvent;
export type EventEvidenceRecord = Record<string, string | number | boolean | null | object | undefined>;
export type RuleExecutionRecord = Record<string, string | number | boolean | null | object | undefined>;

export interface EventsResponse {
  run_id: string;
  video_id?: string;
  summary: EventSummary;
  events: EventRecord[];
  event_evidence: EventEvidenceRecord[];
  rule_executions: RuleExecutionRecord[];
  limit: number;
  event_type?: string | null;
  track_id?: number | null;
}

export interface AlertSummary {
  total_alerts?: number;
  per_alert_type_counts?: Record<string, number>;
  per_level_counts?: Record<string, number>;
  per_status_counts?: Record<string, number>;
  unique_event_ids?: number;
  unique_track_ids?: number;
  first_alert_time_ms?: number | null;
  last_alert_time_ms?: number | null;
  [key: string]: unknown;
}

export type AlertStatus = "new" | "acknowledged" | "resolved" | "ignored";
export type AlertLevel = "info" | "warning" | "critical";

export interface AlertRecord {
  [key: string]: string | number | boolean | null | object | undefined;
  id: string;
  alert_id: string;
  event_id: string;
  video_id: string;
  run_id: string;
  track_id?: number | null;
  event_type?: string | null;
  alert_type: string;
  title: string;
  message: string;
  level: AlertLevel | string;
  status: AlertStatus | string;
  frame_index?: number | null;
  timestamp_ms?: number | null;
  zone_id?: string | null;
  rule_id?: string | null;
  event_evidence_id?: string | null;
  snapshot_path?: string | null;
  acknowledged_by?: string | null;
  acknowledged_at?: string | null;
  resolved_at?: string | null;
  created_at: string;
}

export type TrafficAlert = AlertRecord;

export interface AlertsResponse {
  run_id: string;
  video_id?: string;
  summary: AlertSummary;
  alerts: AlertRecord[];
  limit: number;
  status?: string | null;
  level?: string | null;
  event_type?: string | null;
}

export interface GenerateAlertsResponse {
  run_id: string;
  video_id?: string;
  status: string;
  total_alerts: number;
  alert_summary: AlertSummary;
  artifacts: Record<string, string>;
}

export interface FlowCountRecord {
  [key: string]: string | number | null | undefined;
  event_id?: string;
  track_id?: number | null;
  class_name?: string;
  zone_id?: string;
  counting_line_id?: string;
  direction?: string;
  frame_index?: number;
  timestamp_ms?: number;
}

export interface FlowCountWindow {
  [key: string]: string | number | string[] | number[] | null | undefined;
  time_window_start_ms?: number;
  time_window_end_ms?: number;
  zone_id?: string;
  counting_line_id?: string;
  class_name?: string;
  direction?: string;
  in_count?: number;
  out_count?: number;
  unknown_direction_count?: number;
  total_count?: number;
  track_ids?: number[];
  event_ids?: string[];
}

export interface FlowCountsSummary {
  total_count?: number;
  vehicle_count?: number;
  person_count?: number;
  by_class?: Record<string, number>;
  by_zone?: Record<string, number>;
  by_line?: Record<string, number>;
  by_direction?: Record<string, number>;
  [key: string]: unknown;
}

export interface FlowCountsArtifact {
  schema_version?: string;
  run_id: string;
  video_id?: string;
  generated_at?: string;
  window_ms?: number;
  source_artifacts?: Record<string, string>;
  summary?: FlowCountsSummary;
  windows?: FlowCountWindow[];
  records?: FlowCountRecord[];
}

export interface ZoneStatisticsWindow {
  [key: string]: string | number | number[] | Record<string, number> | null | undefined;
  time_window_start_ms?: number;
  time_window_end_ms?: number;
  zone_id?: string;
  vehicle_count?: number;
  person_count?: number;
  occupancy_count?: number;
  avg_speed_px_per_frame?: number | null;
  class_counts?: Record<string, number>;
  track_ids?: number[];
}

export interface ZoneCongestionEvent {
  [key: string]: string | number | number[] | Record<string, number> | null | undefined;
  event_id?: string;
  zone_id?: string;
  frame_index?: number;
  timestamp_ms?: number;
  vehicle_count?: number;
  avg_speed_px_per_frame?: number | null;
  track_ids?: number[];
  class_counts?: Record<string, number>;
}

export interface ZoneStatisticsSummary {
  zone_count?: number;
  total_windows?: number;
  vehicle_count?: number;
  person_count?: number;
  max_vehicle_count?: number;
  min_avg_speed_px_per_frame?: number | null;
  congestion_event_count?: number;
  [key: string]: unknown;
}

export interface ZoneStatisticsArtifact {
  schema_version?: string;
  run_id: string;
  video_id?: string;
  generated_at?: string;
  window_ms?: number;
  source_artifacts?: Record<string, string>;
  summary?: ZoneStatisticsSummary;
  windows?: ZoneStatisticsWindow[];
  congestion_events?: ZoneCongestionEvent[];
}

export interface AlertCenterResponse {
  alerts: AlertRecord[];
  total: number;
  run_id?: string | null;
  status?: string | null;
  level?: string | null;
}
