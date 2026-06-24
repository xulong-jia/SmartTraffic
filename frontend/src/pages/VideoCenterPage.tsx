import { useEffect, useState } from "react";

import { listAnalysisRuns } from "../api/analysisRuns";
import { listVideos, startVideoProcessing, uploadVideo } from "../api/videos";
import type {
  AnalysisRunSummary,
  DetectionProcessOptions,
  DetectionProcessResult,
  VideoRecord
} from "../types";
import { getRunId } from "../utils/analysisRunMetrics";

type ProcessMode = NonNullable<DetectionProcessOptions["mode"]>;

interface VideoCenterPageProps {
  onOpenAnalysisRun?: (runId: string) => void;
}

export default function VideoCenterPage({ onOpenAnalysisRun }: VideoCenterPageProps) {
  const [videos, setVideos] = useState<VideoRecord[]>([]);
  const [recentRuns, setRecentRuns] = useState<AnalysisRunSummary[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [lastRun, setLastRun] = useState<DetectionProcessResult | null>(null);
  const [processMode, setProcessMode] = useState<ProcessMode>("detection_tracking");
  const [detectorDryRun, setDetectorDryRun] = useState(true);
  const [trackerDryRun, setTrackerDryRun] = useState(true);
  const [frameStride, setFrameStride] = useState(1);
  const [maxFrames, setMaxFrames] = useState(120);
  const [directionWindow, setDirectionWindow] = useState(2);
  const [dwellSpeedThreshold, setDwellSpeedThreshold] = useState(1);
  const [maxHistoryPoints, setMaxHistoryPoints] = useState("");
  const [error, setError] = useState("");
  const [runsError, setRunsError] = useState("");
  const [loading, setLoading] = useState(false);
  const [runsLoading, setRunsLoading] = useState(false);

  useEffect(() => {
    refreshVideos();
    refreshAnalysisRuns();
  }, []);

  function refreshVideos() {
    listVideos()
      .then(setVideos)
      .catch((currentError: Error) => setError(currentError.message));
  }

  async function handleUpload() {
    if (!selectedFile) {
      return;
    }
    setLoading(true);
    setError("");
    try {
      await uploadVideo(selectedFile);
      setSelectedFile(null);
      refreshVideos();
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleProcess(videoId: string) {
    setLoading(true);
    setError("");
    try {
      const options: DetectionProcessOptions = {
        mode: processMode,
        detector_dry_run: detectorDryRun,
        tracker_dry_run: trackerDryRun,
        frame_stride: frameStride,
        max_frames: maxFrames
      };

      if (processMode === "detection_tracking_trajectory") {
        options.direction_window = directionWindow;
        options.dwell_speed_threshold = dwellSpeedThreshold;
        options.max_history_points = parseOptionalPositiveInteger(maxHistoryPoints);
      }

      const result = await startVideoProcessing(videoId, options);
      setLastRun(result);
      refreshVideos();
      refreshAnalysisRuns();
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Detection failed");
    } finally {
      setLoading(false);
    }
  }

  function refreshAnalysisRuns() {
    setRunsLoading(true);
    setRunsError("");
    listAnalysisRuns({ limit: 5 })
      .then((payload) => setRecentRuns(payload.items))
      .catch((currentError: Error) => setRunsError(currentError.message))
      .finally(() => setRunsLoading(false));
  }

  return (
    <>
      <header className="page-header">
        <div>
          <h2>Video Center</h2>
          <p>视频资产与处理状态</p>
        </div>
      </header>
      <section className="panel">
        <div className="toolbar">
          <input
            type="file"
            accept="video/mp4,video/avi,video/quicktime,video/x-matroska,video/webm"
            onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
          />
          <button disabled={!selectedFile || loading} type="button" onClick={handleUpload}>
            Upload
          </button>
        </div>
        {error ? <p>{error}</p> : null}
        {lastRun ? (
          <div className="summary-strip">
            <h3>Latest Process Run</h3>
            <p>
              <strong>{lastRun.run_id}</strong> · {lastRun.status} ·{" "}
              {lastRun.total_frames_processed} frames · {lastRun.total_detections} detections ·{" "}
              {lastRun.total_tracks ?? 0} tracks
              {lastRun.total_trajectory_points !== undefined &&
              lastRun.total_trajectory_points !== null
                ? ` · ${lastRun.total_trajectory_points} trajectory points`
                : ""}
              {lastRun.avg_track_length !== undefined && lastRun.avg_track_length !== null
                ? ` · avg length ${lastRun.avg_track_length}`
                : ""}
              {lastRun.max_track_length !== undefined && lastRun.max_track_length !== null
                ? ` · max length ${lastRun.max_track_length}`
                : ""}
            </p>
          </div>
        ) : null}
        <div className="toolbar">
          <label>
            Mode
            <select
              value={processMode}
              onChange={(event) => setProcessMode(event.target.value as ProcessMode)}
            >
              <option value="detection_only">Detection only</option>
              <option value="detection_tracking">Detection + Tracking</option>
              <option value="detection_tracking_trajectory">
                Detection + Tracking + Trajectory
              </option>
            </select>
          </label>
          <label className="inline-control">
            <input
              checked={detectorDryRun}
              type="checkbox"
              onChange={(event) => setDetectorDryRun(event.target.checked)}
            />
            Detector dry-run
          </label>
          <label className="inline-control">
            <input
              checked={trackerDryRun}
              type="checkbox"
              onChange={(event) => setTrackerDryRun(event.target.checked)}
            />
            Tracker dry-run
          </label>
          <label>
            Stride
            <input
              min={1}
              type="number"
              value={frameStride}
              onChange={(event) => setFrameStride(Math.max(1, Number(event.target.value)))}
            />
          </label>
          <label>
            Max frames
            <input
              min={1}
              type="number"
              value={maxFrames}
              onChange={(event) => setMaxFrames(Math.max(1, Number(event.target.value)))}
            />
          </label>
        </div>
        {processMode === "detection_tracking_trajectory" ? (
          <div className="toolbar">
            <label>
              Direction window
              <input
                min={2}
                type="number"
                value={directionWindow}
                onChange={(event) => setDirectionWindow(Math.max(2, Number(event.target.value)))}
              />
            </label>
            <label>
              Dwell speed threshold
              <input
                min={0}
                step={0.1}
                type="number"
                value={dwellSpeedThreshold}
                onChange={(event) =>
                  setDwellSpeedThreshold(Math.max(0, Number(event.target.value)))
                }
              />
            </label>
            <label>
              Max history points
              <input
                min={1}
                placeholder="unlimited"
                type="number"
                value={maxHistoryPoints}
                onChange={(event) => setMaxHistoryPoints(event.target.value)}
              />
            </label>
          </div>
        ) : null}
        {videos.length === 0 ? (
          <p className="muted">暂无视频</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Filename</th>
                <th>Status</th>
                <th>FPS</th>
                <th>Frames</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {videos.map((video) => (
                <tr key={video.id}>
                  <td>{video.filename}</td>
                  <td>{video.status}</td>
                  <td>{video.fps}</td>
                  <td>{video.total_frames}</td>
                  <td>
                    <button disabled={loading} type="button" onClick={() => handleProcess(video.id)}>
                      Process
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
      <section className="panel">
        <div className="section-heading-row">
          <h3>Recent Analysis Runs</h3>
          <button disabled={runsLoading} type="button" onClick={refreshAnalysisRuns}>
            Refresh
          </button>
        </div>
        {runsLoading ? <p className="muted">Loading analysis runs...</p> : null}
        {runsError ? <p>{runsError}</p> : null}
        {recentRuns.length === 0 && !runsLoading ? (
          <p className="muted">No analysis runs found.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Run ID</th>
                <th>Video ID</th>
                <th>Status</th>
                <th>Updated</th>
                <th>Source</th>
                {onOpenAnalysisRun ? <th>Action</th> : null}
              </tr>
            </thead>
            <tbody>
              {recentRuns.map((run) => (
                <tr key={getRunId(run)}>
                  <td>{getRunId(run)}</td>
                  <td>{formatValue(run.video_id)}</td>
                  <td>{formatValue(run.status)}</td>
                  <td>{formatValue(run.updated_at || run.finished_at)}</td>
                  <td>{formatValue(run.source)}</td>
                  {onOpenAnalysisRun ? (
                    <td>
                      <button type="button" onClick={() => onOpenAnalysisRun(getRunId(run))}>
                        Open
                      </button>
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </>
  );
}

function parseOptionalPositiveInteger(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }

  const parsed = Number.parseInt(trimmed, 10);
  if (!Number.isFinite(parsed)) {
    return null;
  }
  return Math.max(1, parsed);
}

function formatValue(value: string | number | undefined | null): string {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return String(value);
}
