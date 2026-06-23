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

export interface AnalysisRun {
  id: string;
  video_id: string;
  status: string;
  result_dir: string;
  artifact_index: Record<string, string>;
}

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

export type EventRecord = Record<string, string | number | boolean | null | object | undefined>;
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
