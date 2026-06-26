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

export type ReportExportSection =
  | "events"
  | "alerts"
  | "flow_counts"
  | "zone_statistics"
  | "bad_cases"
  | "evaluation_results";

export interface ReportSummaryCounts {
  detections_count: number;
  tracks_count: number;
  trajectory_points_count: number;
  events_count: number;
  alerts_count: number;
  flow_count_records: number;
  zone_statistics_records: number;
  bad_cases_count: number;
  evaluation_results_count: number;
}

export interface ReportSummaryResponse {
  run_id: string;
  run: AnalysisRunSummary;
  counts: ReportSummaryCounts;
  artifact_index: Record<string, unknown>;
  artifact_summary: Record<string, unknown>;
  top_event_types: Record<string, number>;
  alert_status_counts: Record<string, number>;
  flow_totals: Record<string, unknown>;
  bad_case_status_counts: Record<string, number>;
  bad_case_type_counts: Record<string, number>;
  evaluation_metric_summary: Record<string, unknown>;
  available_exports: ReportExportSection[];
  bundle: ReportBundleResponse;
  keyframe_summary: ReportKeyframeSummary;
  annotated_video: ReportAnnotatedVideoSummary;
  note: string;
}

export interface ReportArtifactReference {
  key: string;
  artifact_type: string;
  path?: string | null;
  exists: boolean;
  note: string;
}

export interface ReportKeyframeItem {
  source_type?: string | null;
  source_id?: string | null;
  frame_index?: number | null;
  timestamp_ms?: number | null;
  path?: string | null;
  status: string;
}

export interface ReportKeyframeSummary {
  available: boolean;
  status: string;
  keyframe_count: number;
  keyframe_items: ReportKeyframeItem[];
  index_status: string;
  index_reference?: string | null;
  notes: string;
}

export interface ReportAnnotatedVideoSummary {
  available: boolean;
  status: string;
  annotated_video_available: boolean;
  annotated_video_reference?: string | null;
  record_count: number;
  notes: string;
}

export interface ReportBundleResponse {
  schema_version: string;
  run_id: string;
  generated_at: string;
  included_sections: string[];
  artifact_references: ReportArtifactReference[];
  disclaimer: string;
  note: string;
}

export interface ReportJsonExportResponse {
  metadata: {
    generated_at: string;
    schema_version: string;
    note: string;
    available_exports: ReportExportSection[];
  };
  run: AnalysisRunSummary;
  events: TrafficEvent[];
  alerts: AlertRecord[];
  flow_counts: Array<Record<string, unknown>>;
  zone_statistics: Array<Record<string, unknown>>;
  bad_cases: BadCaseRecord[];
  evaluation_results: EvaluationResultRecord[];
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
  image_size?: number;
  device?: string;
  model_path?: string;
  write_preview?: boolean;
  deepsort_max_age?: number;
  deepsort_n_init?: number;
  deepsort_max_iou_distance?: number;
  deepsort_max_cosine_distance?: number;
  tracking_min_confidence?: number;
  tracking_target_classes?: string[];
  direction_window?: number;
  dwell_speed_threshold?: number;
  max_history_points?: number | null;
  event_rules?: Array<Record<string, unknown>>;
  zones?: Array<Record<string, unknown>>;
  run_events?: boolean;
  generate_alerts?: boolean;
  record_not_matched?: boolean;
}

export interface DirectionConfig {
  start_point?: number[] | null;
  end_point?: number[] | null;
  allowed_angle?: number | null;
  reverse_angle_threshold?: number | null;
}

export interface CountingLineConfig {
  start_point?: number[] | null;
  end_point?: number[] | null;
  in_direction?: string;
  enabled?: boolean;
}

export interface ZoneRecord {
  id: string;
  name: string;
  zone_type: string;
  polygon: number[][];
  direction?: DirectionConfig | null;
  counting_line?: CountingLineConfig | null;
  enabled: boolean;
  video_id?: string | null;
  camera_id?: string | null;
  version: number;
}

export interface ZonePayload {
  id?: string | null;
  name: string;
  zone_type: string;
  polygon: number[][];
  direction?: DirectionConfig | null;
  counting_line?: CountingLineConfig | null;
  enabled: boolean;
  video_id?: string | null;
  camera_id?: string | null;
  version: number;
}

export type ZoneUpdatePayload = Partial<ZonePayload>;

export interface EventRuleRecord {
  id: string;
  name: string;
  event_type: string;
  enabled: boolean;
  zone_id?: string | null;
  target_classes: string[];
  parameters: Record<string, unknown>;
  cooldown_seconds: number;
  severity: string;
  version: number;
  min_track_length: number;
}

export interface EventRulePayload {
  id?: string | null;
  name: string;
  event_type: string;
  enabled: boolean;
  zone_id?: string | null;
  target_classes: string[];
  parameters: Record<string, unknown>;
  cooldown_seconds: number;
  severity: string;
  version: number;
  min_track_length: number;
}

export type EventRuleUpdatePayload = Partial<EventRulePayload>;

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
  total_frames_processed?: number;
  total_detections?: number;
  per_class_counts?: Record<string, number>;
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
  total_frames_processed?: number;
  total_tracks?: number;
  unique_track_ids?: number;
  per_class_track_counts?: Record<string, number>;
  track_state_counts?: Record<string, number>;
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
  id?: string;
  event_id?: string;
  event_type?: string | null;
  track_id?: number | null;
  zone_id?: string | null;
  frame_index?: number | null;
  start_frame?: number | null;
  end_frame?: number | null;
  timestamp_ms?: number | null;
  start_time_ms?: number | null;
  end_time_ms?: number | null;
  class_name?: string | null;
  confidence?: number | null;
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

export type ReviewStatus =
  | "pending"
  | "confirmed"
  | "false_positive"
  | "false_negative"
  | "ignored"
  | "resolved";

export type ReviewAction =
  | "confirm"
  | "mark_false_positive"
  | "add_false_negative"
  | "ignore"
  | "resolve"
  | "comment";

export interface ReviewComment {
  review_id: string;
  run_id: string;
  event_id?: string | null;
  alert_id?: string | null;
  action: ReviewAction | string;
  before_status?: ReviewStatus | string | null;
  after_status: ReviewStatus | string;
  comment: string;
  reviewer: string;
  created_at: string;
  source?: string;
}

export interface ReviewEventSummary {
  run_id: string;
  event_id: string;
  event_type?: string | null;
  track_id?: number | null;
  zone_id?: string | null;
  severity?: string | null;
  original_status: string;
  review_status: ReviewStatus | string;
  last_action?: ReviewAction | string | null;
  comment_count: number;
  linked_alert_ids: string[];
  start_frame?: number | null;
  end_frame?: number | null;
  start_time_ms?: number | null;
  end_time_ms?: number | null;
}

export interface ReviewEventListResponse {
  items: ReviewEventSummary[];
  total: number;
  limit: number;
  offset: number;
}

export type ReviewEventRecord = TrafficEvent & {
  run_id?: string;
  review_status?: ReviewStatus | string;
  original_status?: string;
  linked_alert_ids?: string[];
  comment_count?: number;
  last_action?: ReviewAction | string | null;
};

export interface ReviewEventDetail {
  run_id: string;
  event: ReviewEventRecord;
  review_state?: Record<string, unknown> | null;
  linked_alerts: AlertRecord[];
  comments: ReviewComment[];
  visual_artifacts: Record<string, unknown>;
}

export interface ReviewActionRequest {
  run_id: string;
  comment?: string;
  reviewer?: string;
  alert_id?: string | null;
}

export interface ReviewActionResponse {
  run_id: string;
  event_id: string;
  status: ReviewStatus | string;
  review_id: string;
  review: ReviewComment;
  state: Record<string, unknown>;
}

export interface ReviewCommentRequest {
  run_id: string;
  event_id: string;
  comment: string;
  reviewer?: string;
  alert_id?: string | null;
}

export interface ReviewCommentsResponse {
  run_id: string;
  event_id?: string | null;
  items: ReviewComment[];
  total: number;
  limit: number;
  offset: number;
}

export interface FalseNegativeRequest {
  run_id: string;
  expected_event_type: string;
  zone_id?: string | null;
  track_id?: number | null;
  start_frame?: number | null;
  end_frame?: number | null;
  start_time_ms?: number | null;
  end_time_ms?: number | null;
  description: string;
  reviewer?: string;
}

export interface FalseNegativeRecord {
  false_negative_id: string;
  run_id: string;
  expected_event_type: string;
  zone_id?: string | null;
  track_id?: number | null;
  start_frame?: number | null;
  end_frame?: number | null;
  start_time_ms?: number | null;
  end_time_ms?: number | null;
  description: string;
  reviewer: string;
  created_at: string;
  status: "false_negative" | string;
  source?: string;
}

export interface FalseNegativeResponse {
  run_id: string;
  status: "false_negative";
  false_negative: FalseNegativeRecord;
  review: ReviewComment;
  state: Record<string, unknown>;
}

export type BadCaseType =
  | "false_positive"
  | "false_negative"
  | "detection_miss"
  | "detection_false_positive"
  | "tracking_fragmentation"
  | "id_switch"
  | "trajectory_error"
  | "event_rule_error"
  | "annotation_error"
  | "other";

export type BadCaseModule =
  | "detector"
  | "tracker"
  | "trajectory"
  | "event_engine"
  | "review_center"
  | "visualization"
  | "other";

export type BadCaseStatus = "open" | "triaged" | "fixed" | "verified" | "wont_fix";
export type BadCaseSource =
  | "manual"
  | "review_center"
  | "evaluation"
  | "evaluation_center"
  | "import";

export interface BadCaseRecord {
  case_id: string;
  run_id: string;
  video_id?: string | null;
  event_id?: string | null;
  track_id?: number | null;
  frame_index?: number | null;
  case_type: BadCaseType | string;
  module: BadCaseModule | string;
  description: string;
  expected_result: string;
  actual_result: string;
  root_cause: string;
  snapshot_path?: string | null;
  tags: string[];
  status: BadCaseStatus | string;
  source: BadCaseSource | string;
  linked_review_id?: string | null;
  linked_failed_case_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface BadCaseSummary {
  total: number;
  by_type: Record<string, number>;
  by_module: Record<string, number>;
  by_status: Record<string, number>;
  by_source?: Record<string, number>;
  by_tag: Record<string, number>;
  top_tags?: Record<string, number>;
}

export interface BadCaseListResponse {
  items: BadCaseRecord[];
  total: number;
  limit: number;
  offset: number;
  summary: BadCaseSummary;
}

export interface BadCaseListParams {
  run_id?: string;
  case_type?: string;
  module?: string;
  status?: string;
  tag?: string;
  limit?: number;
  offset?: number;
}

export interface BadCaseCreateRequest {
  run_id: string;
  video_id?: string | null;
  event_id?: string | null;
  track_id?: number | null;
  frame_index?: number | null;
  case_type: BadCaseType | string;
  module: BadCaseModule | string;
  description?: string;
  expected_result?: string;
  actual_result?: string;
  root_cause?: string;
  snapshot_path?: string | null;
  tags?: string[];
  source?: BadCaseSource | string;
  linked_review_id?: string | null;
  linked_failed_case_id?: string | null;
}

export interface BadCaseUpdateRequest {
  run_id?: string;
  status?: BadCaseStatus | string;
  root_cause?: string;
  tags?: string[];
  description?: string;
  expected_result?: string;
  actual_result?: string;
  snapshot_path?: string | null;
  linked_failed_case_id?: string | null;
}

export interface BadCaseFromReviewRequest {
  run_id: string;
  event_id?: string | null;
  review_id?: string | null;
  case_type?: BadCaseType | string | null;
  module?: BadCaseModule | string;
  description?: string | null;
  expected_result?: string | null;
  actual_result?: string | null;
  root_cause?: string | null;
  tags?: string[] | null;
}

export interface BadCaseFromFailedCaseRequest {
  run_id: string;
  failed_case_id: string;
  case_type?: BadCaseType | string | null;
  module?: BadCaseModule | string | null;
  description?: string | null;
  expected_result?: string | null;
  actual_result?: string | null;
  root_cause?: string | null;
  tags?: string[] | null;
}

export type EvaluationType =
  | "event"
  | "flow_counting"
  | "trajectory"
  | "detection"
  | "tracking"
  | "regression";

export interface EvaluationDatasetRecord {
  dataset_id: string;
  name: string;
  dataset_type: EvaluationType | string;
  source: string;
  annotation_path?: string | null;
  expected_events_path?: string | null;
  expected_counts_path?: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface EvaluationDatasetCreateRequest {
  dataset_id: string;
  name: string;
  dataset_type: EvaluationType | string;
  source?: string;
  annotation_path?: string | null;
  expected_events_path?: string | null;
  expected_counts_path?: string | null;
  metadata?: Record<string, unknown>;
}

export interface EvaluationDatasetListResponse {
  schema_version: string;
  datasets: EvaluationDatasetRecord[];
}

export interface EvaluationRunRecord {
  evaluation_run_id: string;
  dataset_id?: string | null;
  run_id: string;
  evaluation_type: EvaluationType | string;
  status: string;
  started_at: string;
  finished_at: string;
  config: Record<string, unknown>;
}

export interface EvaluationResultRecord {
  evaluation_result_id: string;
  evaluation_run_id: string;
  run_id: string;
  dataset_id?: string | null;
  evaluation_type: EvaluationType | string;
  metric_name: string;
  metric_value?: number | string | null;
  details: Record<string, unknown>;
  created_at: string;
}

export interface EvaluationFailedCaseRecord {
  failed_case_id: string;
  evaluation_run_id: string;
  run_id: string;
  dataset_id?: string | null;
  failure_type: string;
  module: string;
  expected: Record<string, unknown>;
  actual: Record<string, unknown>;
  frame_range: Record<string, number | null | undefined>;
  suggested_bad_case_type?: string | null;
  created_at: string;
}

export interface EvaluationSummaryArtifact {
  schema_version: string;
  run_id: string;
  generated_at?: string | null;
  summary: Record<string, unknown>;
  failed_cases: EvaluationFailedCaseRecord[];
}

export interface BadCaseRegressionSummary {
  status?: string;
  total_cases?: number;
  open_cases?: number;
  fixed_cases?: number;
  verified_cases?: number;
  ignored_cases?: number;
  fixed_case_count?: number;
  reopened_case_count?: number;
  regression_pass_rate?: number;
  definition?: string;
  reason?: string;
}

export interface EvaluationRunRequest {
  run_id: string;
  dataset_id?: string | null;
  evaluation_type: EvaluationType | string;
  config?: Record<string, unknown>;
}

export interface EvaluationRunResponse {
  evaluation_run: EvaluationRunRecord;
  results: EvaluationResultRecord[];
  summary: EvaluationSummaryArtifact;
  failed_cases: EvaluationFailedCaseRecord[];
}

export interface EvaluationRunListResponse {
  items: EvaluationRunRecord[];
  total: number;
  limit: number;
  offset: number;
}

export interface EvaluationResultListResponse {
  items: EvaluationResultRecord[];
  total: number;
  limit: number;
  offset: number;
}

export interface EvaluationFailedCaseListResponse {
  items: EvaluationFailedCaseRecord[];
  total: number;
  limit: number;
  offset: number;
}
