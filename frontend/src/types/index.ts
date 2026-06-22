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
