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
  mode?: "detection_only" | "detection_tracking";
  dry_run?: boolean;
  detector_dry_run?: boolean;
  tracker_dry_run?: boolean;
  frame_stride?: number;
  max_frames?: number;
  conf_threshold?: number;
  iou_threshold?: number;
  write_preview?: boolean;
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
  per_class_counts: Record<string, number>;
  per_class_track_counts?: Record<string, number> | null;
  track_state_counts?: Record<string, number> | null;
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
