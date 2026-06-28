import { useEffect, useState } from "react";

import { listAnalysisRuns } from "../api/analysisRuns";
import { listVideos, startVideoProcessing, uploadVideo } from "../api/videos";
import CollapsibleSection from "../components/CollapsibleSection";
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
          <h2>视频中心</h2>
          <p>上传视频、查看元数据，并创建本地分析任务。</p>
        </div>
      </header>
      <section className="panel upload-panel">
        <div className="toolbar">
          <input
            type="file"
            accept="video/mp4,video/avi,video/quicktime,video/x-matroska,video/webm"
            onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
          />
          <button
            className="primary-action"
            disabled={!selectedFile || loading}
            type="button"
            onClick={handleUpload}
          >
            上传
          </button>
        </div>
        {error ? <p className="alert-box error">{error}</p> : null}
        {lastRun ? (
          <div className="summary-strip">
            <h3>最新处理任务</h3>
            <p>
              <strong>{lastRun.run_id}</strong> ·{" "}
              <span className={`status-pill status-${statusClassName(lastRun.status)}`}>
                {lastRun.status}
              </span>{" "}
              ·{" "}
              {lastRun.total_frames_processed} 帧 · {lastRun.total_detections} 检测 ·{" "}
              {lastRun.total_tracks ?? 0} 轨迹
              {lastRun.total_trajectory_points !== undefined &&
              lastRun.total_trajectory_points !== null
                ? ` · ${lastRun.total_trajectory_points} 轨迹点`
                : ""}
              {lastRun.avg_track_length !== undefined && lastRun.avg_track_length !== null
                ? ` · 平均长度 ${lastRun.avg_track_length}`
                : ""}
              {lastRun.max_track_length !== undefined && lastRun.max_track_length !== null
                ? ` · 最大长度 ${lastRun.max_track_length}`
                : ""}
            </p>
          </div>
        ) : null}
        <div className="summary-strip process-panel">
          <h3>处理参数</h3>
          <div className="toolbar">
            <label>
              模式
              <select
                value={processMode}
                onChange={(event) => setProcessMode(event.target.value as ProcessMode)}
              >
                <option value="detection_only">仅检测</option>
                <option value="detection_tracking">检测 + 跟踪</option>
                <option value="detection_tracking_trajectory">
                  检测 + 跟踪 + 轨迹
                </option>
              </select>
            </label>
          </div>
          <CollapsibleSection title="检测与跟踪参数" className="compact-section">
            <div className="toolbar">
              <label className="inline-control">
                <input
                  checked={detectorDryRun}
                  type="checkbox"
                  onChange={(event) => setDetectorDryRun(event.target.checked)}
                />
                检测模拟模式
              </label>
              <label className="inline-control">
                <input
                  checked={trackerDryRun}
                  type="checkbox"
                  onChange={(event) => setTrackerDryRun(event.target.checked)}
                />
                跟踪模拟模式
              </label>
              <label>
                抽帧步长
                <input
                  min={1}
                  type="number"
                  value={frameStride}
                  onChange={(event) => setFrameStride(Math.max(1, Number(event.target.value)))}
                />
              </label>
              <label>
                最大帧数
                <input
                  min={1}
                  type="number"
                  value={maxFrames}
                  onChange={(event) => setMaxFrames(Math.max(1, Number(event.target.value)))}
                />
              </label>
            </div>
            {processMode === "detection_tracking_trajectory" ? (
              <div className="toolbar compact">
                <label>
                  方向窗口
                  <input
                    min={2}
                    type="number"
                    value={directionWindow}
                    onChange={(event) =>
                      setDirectionWindow(Math.max(2, Number(event.target.value)))
                    }
                  />
                </label>
                <label>
                  停留速度阈值
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
                  最大历史点
                  <input
                    min={1}
                    placeholder="不限制"
                    type="number"
                    value={maxHistoryPoints}
                    onChange={(event) => setMaxHistoryPoints(event.target.value)}
                  />
                </label>
              </div>
            ) : null}
          </CollapsibleSection>
        </div>
        {videos.length === 0 ? (
          <p className="empty-state">暂无视频。请上传一个本地视频开始分析。</p>
        ) : (
          <div className="table-scroll">
            <table className="data-table">
              <caption className="sr-only">视频列表</caption>
              <thead>
                <tr>
                  <th scope="col">文件名</th>
                  <th scope="col">状态</th>
                  <th scope="col">FPS</th>
                  <th scope="col">帧数</th>
                  <th scope="col">操作</th>
                </tr>
              </thead>
              <tbody>
                {videos.map((video) => (
                  <tr key={video.id}>
                    <td className="cell-path">{video.filename}</td>
                    <td>
                      <span className={`status-pill status-${statusClassName(video.status)}`}>
                        {video.status}
                      </span>
                    </td>
                    <td>{video.fps}</td>
                    <td>{video.total_frames}</td>
                    <td>
                      <button
                        className="primary-action"
                        disabled={loading}
                        type="button"
                        onClick={() => handleProcess(video.id)}
                      >
                        开始分析
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      <section className="panel">
        <div className="section-heading-row">
          <h3>最近分析任务</h3>
          <button disabled={runsLoading} type="button" onClick={refreshAnalysisRuns}>
            刷新
          </button>
        </div>
        {runsLoading ? <p className="muted">正在加载分析任务...</p> : null}
        {runsError ? <p className="alert-box error">{runsError}</p> : null}
        {recentRuns.length === 0 && !runsLoading ? (
          <p className="empty-state">暂无分析任务。请先在视频中心上传视频并启动分析。</p>
        ) : (
          <div className="table-scroll">
            <table className="data-table">
              <caption className="sr-only">最近分析任务</caption>
              <thead>
                <tr>
                  <th scope="col">Run ID</th>
                  <th scope="col">Video ID</th>
                  <th scope="col">状态</th>
                  <th scope="col">更新时间</th>
                  <th scope="col">来源</th>
                  {onOpenAnalysisRun ? <th scope="col">操作</th> : null}
                </tr>
              </thead>
              <tbody>
                {recentRuns.map((run) => (
                  <tr key={getRunId(run)}>
                    <td className="cell-id">{getRunId(run)}</td>
                    <td className="cell-id">{formatValue(run.video_id)}</td>
                    <td>
                      <span className={`status-pill status-${statusClassName(run.status)}`}>
                        {formatValue(run.status)}
                      </span>
                    </td>
                    <td>{formatValue(run.updated_at || run.finished_at)}</td>
                    <td>{formatValue(run.source)}</td>
                    {onOpenAnalysisRun ? (
                      <td>
                        <button type="button" onClick={() => onOpenAnalysisRun(getRunId(run))}>
                          打开
                        </button>
                      </td>
                    ) : null}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
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

function statusClassName(value: string | number | undefined | null): string {
  const raw = formatValue(value).toLowerCase().replace(/[^a-z0-9_-]+/g, "_");
  return raw || "unknown";
}
