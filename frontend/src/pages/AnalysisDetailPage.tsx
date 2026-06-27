import { useEffect, useState } from "react";

import {
  generateAlerts,
  getAnalysisRun,
  getAnalysisRunDetections,
  getAnalysisRunFlowCounts,
  getAnalysisRunManifest,
  getAnalysisRunAlerts,
  getAnalysisRunEvents,
  getAnalysisRunTracks,
  getAnalysisRunTrajectoryPoints,
  getAnalysisRunZoneStatistics,
  listAnalysisRuns
} from "../api/analysisRuns";
import { listZones } from "../api/zones";
import EventTable from "../components/EventTable";
import EventTimeline from "../components/EventTimeline";
import VideoPlayerWithOverlay from "../components/VideoPlayerWithOverlay";
import type {
  AlertRecord,
  AlertsResponse,
  AnalysisRunSummary,
  AnalysisRunDetections,
  AnalysisRunTracks,
  ArtifactAvailability,
  ArtifactSummaryItem,
  ArtifactSummary,
  FlowCountsArtifact,
  EventEvidenceRecord,
  EventRecord,
  EventsResponse,
  RuleExecutionRecord,
  TrajectoryFrame,
  TrajectoryPointRow,
  TrajectoryPointsResponse,
  ZoneRecord,
  ZoneStatisticsArtifact
} from "../types";
import { buildOverlayDataBundle, inferOverlaySize } from "../utils/analysisDetailMapping";
import { formatDisplayValue as formatValue } from "../utils/format";
import { getEventSeekTimeMs } from "../utils/eventTimeline";
import { getRunId } from "../utils/analysisRunMetrics";
import { buildReviewLink } from "../utils/reviewNavigation";

const trajectoryColumns: Array<keyof TrajectoryPointRow> = [
  "frame_index",
  "timestamp_ms",
  "track_id",
  "class_name",
  "state",
  "speed_px_per_frame",
  "speed_px_per_second",
  "moving_angle",
  "track_length"
];

const evidenceColumns = ["event_id", "evidence_type", "frame_index", "track_id"] as const;

const ruleExecutionColumns = ["rule_id", "status", "track_id", "frame_index"] as const;

const alertColumns = [
  "alert_type",
  "level",
  "status",
  "event_type",
  "track_id",
  "zone_id",
  "frame_index",
  "timestamp_ms"
] as const;

interface AnalysisDetailPageProps {
  initialRunId?: string;
  onOpenReview?: (href: string) => void;
}

export default function AnalysisDetailPage({
  initialRunId = "",
  onOpenReview
}: AnalysisDetailPageProps) {
  const [runs, setRuns] = useState<AnalysisRunSummary[]>([]);
  const [selectedRunId, setSelectedRunId] = useState("");
  const [runsLoading, setRunsLoading] = useState(false);
  const [runsError, setRunsError] = useState("");
  const [runSummary, setRunSummary] = useState<AnalysisRunSummary | null>(null);
  const [runSummaryLoading, setRunSummaryLoading] = useState(false);
  const [runSummaryError, setRunSummaryError] = useState("");
  const [manifestPayload, setManifestPayload] = useState<Record<string, unknown> | null>(null);
  const [manifestLoading, setManifestLoading] = useState(false);
  const [manifestError, setManifestError] = useState("");
  const [detections, setDetections] = useState<AnalysisRunDetections | null>(null);
  const [detectionsLoading, setDetectionsLoading] = useState(false);
  const [detectionsError, setDetectionsError] = useState("");
  const [tracks, setTracks] = useState<AnalysisRunTracks | null>(null);
  const [tracksLoading, setTracksLoading] = useState(false);
  const [tracksError, setTracksError] = useState("");
  const [trajectoryData, setTrajectoryData] = useState<TrajectoryPointsResponse | null>(null);
  const [trajectoryLoading, setTrajectoryLoading] = useState(false);
  const [trajectoryError, setTrajectoryError] = useState("");
  const [trajectoryTrackIdFilter, setTrajectoryTrackIdFilter] = useState("");
  const [trajectoryLimit, setTrajectoryLimit] = useState(100);
  const [eventsData, setEventsData] = useState<EventsResponse | null>(null);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [eventsError, setEventsError] = useState("");
  const [eventTypeFilter, setEventTypeFilter] = useState("");
  const [eventTrackIdFilter, setEventTrackIdFilter] = useState("");
  const [eventLimit, setEventLimit] = useState(100);
  const [alertsData, setAlertsData] = useState<AlertsResponse | null>(null);
  const [alertsLoading, setAlertsLoading] = useState(false);
  const [alertsError, setAlertsError] = useState("");
  const [alertStatusFilter, setAlertStatusFilter] = useState("");
  const [alertLevelFilter, setAlertLevelFilter] = useState("");
  const [alertEventTypeFilter, setAlertEventTypeFilter] = useState("");
  const [alertLimit, setAlertLimit] = useState(100);
  const [flowCountsData, setFlowCountsData] = useState<FlowCountsArtifact | null>(null);
  const [flowCountsLoading, setFlowCountsLoading] = useState(false);
  const [flowCountsError, setFlowCountsError] = useState("");
  const [zoneStatisticsData, setZoneStatisticsData] = useState<ZoneStatisticsArtifact | null>(null);
  const [zoneStatisticsLoading, setZoneStatisticsLoading] = useState(false);
  const [zoneStatisticsError, setZoneStatisticsError] = useState("");
  const [zones, setZones] = useState<ZoneRecord[]>([]);
  const [zonesLoading, setZonesLoading] = useState(false);
  const [zonesError, setZonesError] = useState("");
  const [currentTimeMs, setCurrentTimeMs] = useState(0);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);

  useEffect(() => {
    const requestedRunId = initialRunId.trim();
    setRunsLoading(true);
    setRunsError("");
    listAnalysisRuns({ limit: 50 })
      .then((payload) => {
        setRuns(payload.items);
        if (requestedRunId) {
          setSelectedRunId(requestedRunId);
          return;
        }
        setSelectedRunId((currentRunId) => currentRunId || getRunId(payload.items[0] ?? { id: "", status: "" }));
      })
      .catch((currentError: Error) => setRunsError(currentError.message))
      .finally(() => setRunsLoading(false));
  }, [initialRunId]);

  useEffect(() => {
    if (!selectedRunId) {
      return;
    }
    loadRunSummary(selectedRunId);
    loadManifest(selectedRunId);
    loadDetections(selectedRunId);
    loadTracks(selectedRunId);
    loadTrajectory(selectedRunId);
    loadEvents(selectedRunId);
    loadAlerts(selectedRunId);
    loadFlowCounts(selectedRunId);
    loadZoneStatistics(selectedRunId);
    loadZonesForOverlay();
    setCurrentTimeMs(0);
    setSelectedEventId(null);
  }, [selectedRunId]);

  useEffect(() => {
    const requestedRunId = initialRunId.trim();
    if (requestedRunId) {
      setSelectedRunId(requestedRunId);
    }
  }, [initialRunId]);

  async function loadRunSummary(runId: string) {
    setRunSummaryLoading(true);
    setRunSummaryError("");
    setRunSummary(null);
    try {
      setRunSummary(await getAnalysisRun(runId));
    } catch (currentError) {
      setRunSummaryError(
        currentError instanceof Error ? currentError.message : "Run summary request failed"
      );
    } finally {
      setRunSummaryLoading(false);
    }
  }

  async function loadManifest(runId: string) {
    setManifestLoading(true);
    setManifestError("");
    setManifestPayload(null);
    try {
      setManifestPayload(await getAnalysisRunManifest(runId));
    } catch (currentError) {
      setManifestError(currentError instanceof Error ? currentError.message : "Manifest request failed");
    } finally {
      setManifestLoading(false);
    }
  }

  async function loadDetections(runId: string) {
    setDetectionsLoading(true);
    setDetectionsError("");
    setDetections(null);
    try {
      setDetections(await getAnalysisRunDetections(runId, 50));
    } catch (currentError) {
      setDetectionsError(
        currentError instanceof Error ? currentError.message : "Detections request failed"
      );
    } finally {
      setDetectionsLoading(false);
    }
  }

  async function loadTracks(runId: string) {
    setTracksLoading(true);
    setTracksError("");
    setTracks(null);
    try {
      setTracks(await getAnalysisRunTracks(runId, 50));
    } catch (currentError) {
      setTracksError(currentError instanceof Error ? currentError.message : "Tracks request failed");
    } finally {
      setTracksLoading(false);
    }
  }

  async function loadTrajectory(runId: string) {
    setTrajectoryLoading(true);
    setTrajectoryError("");
    setTrajectoryData(null);
    try {
      const payload = await getAnalysisRunTrajectoryPoints(runId, {
        limit: trajectoryLimit,
        trackId: parseTrackIdFilter(trajectoryTrackIdFilter)
      });
      setTrajectoryData(payload);
    } catch (currentError) {
      const message =
        currentError instanceof Error ? currentError.message : "Trajectory request failed";
      if (message.includes("404")) {
        setTrajectoryError("当前 run 无轨迹产物，请使用 detection_tracking_trajectory 模式重新处理。");
      } else {
        setTrajectoryError(message);
      }
    } finally {
      setTrajectoryLoading(false);
    }
  }

  function handleTrajectoryRefresh() {
    if (!selectedRunId) {
      return;
    }
    if (trajectoryTrackIdFilter.trim() && parseTrackIdFilter(trajectoryTrackIdFilter) === null) {
      setTrajectoryError("Track ID must be an integer.");
      return;
    }
    loadTrajectory(selectedRunId);
  }

  async function loadEvents(runId: string) {
    setEventsLoading(true);
    setEventsError("");
    setEventsData(null);
    try {
      const payload = await getAnalysisRunEvents(runId, {
        limit: eventLimit,
        eventType: normalizeOptionalString(eventTypeFilter),
        trackId: parseTrackIdFilter(eventTrackIdFilter)
      });
      setEventsData(payload);
    } catch (currentError) {
      const message = currentError instanceof Error ? currentError.message : "Events request failed";
      if (message.includes("404")) {
        setEventsError("当前 run 无事件产物");
      } else {
        setEventsError(message);
      }
    } finally {
      setEventsLoading(false);
    }
  }

  function handleEventsRefresh() {
    if (!selectedRunId) {
      return;
    }
    if (eventTrackIdFilter.trim() && parseTrackIdFilter(eventTrackIdFilter) === null) {
      setEventsError("Track ID must be an integer.");
      return;
    }
    loadEvents(selectedRunId);
  }

  async function loadAlerts(runId: string) {
    setAlertsLoading(true);
    setAlertsError("");
    setAlertsData(null);
    try {
      const payload = await getAnalysisRunAlerts(runId, {
        limit: alertLimit,
        status: normalizeOptionalString(alertStatusFilter),
        level: normalizeOptionalString(alertLevelFilter),
        eventType: normalizeOptionalString(alertEventTypeFilter)
      });
      setAlertsData(payload);
    } catch (currentError) {
      const message = currentError instanceof Error ? currentError.message : "Alerts request failed";
      if (message.includes("404")) {
        setAlertsError("当前 run 无告警产物，可先从事件生成告警。");
      } else {
        setAlertsError(message);
      }
    } finally {
      setAlertsLoading(false);
    }
  }

  async function loadFlowCounts(runId: string) {
    setFlowCountsLoading(true);
    setFlowCountsError("");
    setFlowCountsData(null);
    try {
      setFlowCountsData(await getAnalysisRunFlowCounts(runId));
    } catch (currentError) {
      const message =
        currentError instanceof Error ? currentError.message : "Flow counts request failed";
      if (message.includes("404")) {
        setFlowCountsError("当前 run 无 flow_counts.json 产物。");
      } else {
        setFlowCountsError(message);
      }
    } finally {
      setFlowCountsLoading(false);
    }
  }

  async function loadZoneStatistics(runId: string) {
    setZoneStatisticsLoading(true);
    setZoneStatisticsError("");
    setZoneStatisticsData(null);
    try {
      setZoneStatisticsData(await getAnalysisRunZoneStatistics(runId));
    } catch (currentError) {
      const message =
        currentError instanceof Error ? currentError.message : "Zone statistics request failed";
      if (message.includes("404")) {
        setZoneStatisticsError("当前 run 无 zone_statistics.json 产物。");
      } else {
        setZoneStatisticsError(message);
      }
    } finally {
      setZoneStatisticsLoading(false);
    }
  }

  async function loadZonesForOverlay(videoId?: string | null) {
    setZonesLoading(true);
    setZonesError("");
    try {
      setZones(await listZones(videoId ? { videoId } : {}));
    } catch (currentError) {
      setZonesError(currentError instanceof Error ? currentError.message : "Zones request failed");
    } finally {
      setZonesLoading(false);
    }
  }

  function handleAlertsRefresh() {
    if (!selectedRunId) {
      return;
    }
    loadAlerts(selectedRunId);
  }

  async function handleGenerateAlerts() {
    if (!selectedRunId) {
      return;
    }
    setAlertsLoading(true);
    setAlertsError("");
    try {
      await generateAlerts(selectedRunId);
      await loadAlerts(selectedRunId);
    } catch (currentError) {
      const message =
        currentError instanceof Error ? currentError.message : "Generate alerts request failed";
      if (message.includes("404")) {
        setAlertsError("当前 run 无事件产物，无法生成告警。");
      } else {
        setAlertsError(message);
      }
    } finally {
      setAlertsLoading(false);
    }
  }

  const overlayData = buildOverlayDataBundle({
    detections,
    tracks,
    trajectory: trajectoryData,
    events: eventsData,
    zones,
    selectedEventId
  });
  const overlaySize = inferOverlaySize({ detections, tracks, zones });
  const videoUrl = normalizeVideoUrl(runSummary?.artifact_paths?.annotated_video);

  return (
    <>
      <header className="page-header">
        <div>
          <h2>分析详情 Analysis Detail</h2>
          <p>查看检测、跟踪、轨迹、事件证据和分析产物。</p>
        </div>
      </header>
      <div className="grid two review-workspace">
        <VideoPlayerWithOverlay
          currentTimeMs={currentTimeMs}
          detections={overlayData.detections}
          height={overlaySize.height}
          onSeek={setCurrentTimeMs}
          selectedEventId={selectedEventId}
          selectedTrackId={overlayData.selectedTrackId}
          selectedZoneId={overlayData.selectedZoneId}
          title="视频叠加 Video Overlay"
          tracks={overlayData.tracks}
          trajectoryPoints={overlayData.trajectoryFrames}
          videoUrl={videoUrl}
          width={overlaySize.width}
          zones={overlayData.zones}
        />
        <div className="grid">
          <EventTimeline
            error={eventsError}
            events={overlayData.events}
            loading={eventsLoading}
            onSeek={setCurrentTimeMs}
            onSelectEvent={(eventId, event) => {
              setSelectedEventId(eventId);
              setCurrentTimeMs(getEventSeekTimeMs(event));
            }}
            selectedEventId={selectedEventId}
          />
          <section className="panel">
            <h3>叠加数据 Overlay Data</h3>
            {zonesLoading ? <p className="muted">正在加载区域...</p> : null}
            {zonesError ? <p>{zonesError}</p> : null}
            <p>
              {overlayData.detections.length} 检测帧 detection frames ·{" "}
              {overlayData.tracks.length} 跟踪帧 track frames ·{" "}
              {overlayData.trajectoryFrames.length} 轨迹帧 trajectory frames ·{" "}
              {overlayData.zones.length} 区域 zones
            </p>
          </section>
        </div>
      </div>
      <div className="grid two">
        <div className="grid">
          <section className="panel">
            <label>
              分析任务 Run ID
              <select
                value={selectedRunId}
                onChange={(event) => setSelectedRunId(event.target.value)}
              >
                <option value="">未选择分析任务 No run selected</option>
                {selectedRunId && !runs.some((run) => getRunId(run) === selectedRunId) ? (
                  <option value={selectedRunId}>{selectedRunId}</option>
                ) : null}
                {runs.map((run) => (
                  <option key={getRunId(run)} value={getRunId(run)}>
                    {getRunId(run)}
                  </option>
                ))}
              </select>
            </label>
            {runsLoading ? <p className="muted">正在加载任务索引...</p> : null}
            {runsError ? <p>{runsError}</p> : null}
            {runs.length === 0 && !runsLoading ? (
              <p className="muted">暂无分析任务。请先在视频中心上传视频并启动分析。</p>
            ) : null}
          </section>
          <section className="panel">
            <h3>任务摘要 Run Summary</h3>
            {runSummaryLoading ? <p className="muted">正在加载任务摘要...</p> : null}
            {runSummaryError ? <p>{runSummaryError}</p> : null}
            {runSummary ? <RunSummaryPanel run={runSummary} /> : null}
          </section>
          <section className="panel">
            <h3>索引状态 Index Status</h3>
            {manifestLoading ? <p className="muted">正在加载 manifest...</p> : null}
            {manifestError ? <p>{manifestError}</p> : null}
            {runSummary ? (
              <IndexStatusPanel manifestPayload={manifestPayload} run={runSummary} />
            ) : (
              <p className="muted">请选择一个分析任务，查看 metadata、manifest 和 artifact index。</p>
            )}
          </section>
          <section className="panel">
            <h3>产物摘要 Artifact Summary</h3>
            <ArtifactSummaryTable artifactSummary={runSummary?.artifact_summary} />
          </section>
          <section className="panel">
            <h3>可视化产物 Visual Artifacts</h3>
            <VisualArtifactsPanel artifactSummary={runSummary?.artifact_summary} />
          </section>
        </div>
        <div className="grid">
          <section className="panel">
            <h3>轨迹查询 Trajectory Query</h3>
            <div className="toolbar">
              <label>
                条数 Limit
                <input
                  max={1000}
                  min={0}
                  type="number"
                  value={trajectoryLimit}
                  onChange={(event) =>
                    setTrajectoryLimit(clampInteger(Number(event.target.value), 0, 1000))
                  }
                />
              </label>
              <label>
                Track ID
                <input
                  placeholder="all"
                  type="number"
                  value={trajectoryTrackIdFilter}
                  onChange={(event) => setTrajectoryTrackIdFilter(event.target.value)}
                />
              </label>
              <button disabled={!selectedRunId || trajectoryLoading} type="button" onClick={handleTrajectoryRefresh}>
                应用 / 刷新 Apply / Refresh
              </button>
            </div>
            {trajectoryLoading ? <p className="muted">正在加载轨迹点...</p> : null}
            {trajectoryError ? <p>{trajectoryError}</p> : null}
            {trajectoryData ? <TrajectoryDetail data={trajectoryData} /> : null}
          </section>
          <section className="panel">
            <h3>事件查询 Event Query</h3>
            <div className="toolbar">
              <label>
                条数 Limit
                <input
                  max={1000}
                  min={0}
                  type="number"
                  value={eventLimit}
                  onChange={(event) =>
                    setEventLimit(clampInteger(Number(event.target.value), 0, 1000))
                  }
                />
              </label>
              <label>
                事件类型 Event type
                <input
                  placeholder="all"
                  value={eventTypeFilter}
                  onChange={(event) => setEventTypeFilter(event.target.value)}
                />
              </label>
              <label>
                Track ID
                <input
                  placeholder="all"
                  type="number"
                  value={eventTrackIdFilter}
                  onChange={(event) => setEventTrackIdFilter(event.target.value)}
                />
              </label>
              <button disabled={!selectedRunId || eventsLoading} type="button" onClick={handleEventsRefresh}>
                应用 / 刷新 Apply / Refresh
              </button>
            </div>
            {eventsLoading ? <p className="muted">正在加载事件...</p> : null}
            {eventsError ? <p>{eventsError}</p> : null}
            {eventsData ? (
              <EventsDetail
                data={eventsData}
                onOpenReview={onOpenReview}
                onSelectEvent={(eventId, event) => {
                  setSelectedEventId(eventId);
                  setCurrentTimeMs(getEventSeekTimeMs(event));
                }}
                selectedEventId={selectedEventId}
              />
            ) : null}
          </section>
          <section className="panel">
            <h3>告警查询 Alert Query</h3>
            <div className="toolbar">
              <label>
                条数 Limit
                <input
                  max={1000}
                  min={0}
                  type="number"
                  value={alertLimit}
                  onChange={(event) =>
                    setAlertLimit(clampInteger(Number(event.target.value), 0, 1000))
                  }
                />
              </label>
              <label>
                状态 Status
                <input
                  placeholder="all"
                  value={alertStatusFilter}
                  onChange={(event) => setAlertStatusFilter(event.target.value)}
                />
              </label>
              <label>
                级别 Level
                <input
                  placeholder="all"
                  value={alertLevelFilter}
                  onChange={(event) => setAlertLevelFilter(event.target.value)}
                />
              </label>
              <label>
                事件类型 Event type
                <input
                  placeholder="all"
                  value={alertEventTypeFilter}
                  onChange={(event) => setAlertEventTypeFilter(event.target.value)}
                />
              </label>
              <button disabled={!selectedRunId || alertsLoading} type="button" onClick={handleGenerateAlerts}>
                从事件生成告警 Generate alerts
              </button>
              <button disabled={!selectedRunId || alertsLoading} type="button" onClick={handleAlertsRefresh}>
                刷新告警 Refresh alerts
              </button>
            </div>
            {alertsLoading ? <p className="muted">正在加载告警...</p> : null}
            {alertsError ? <p>{alertsError}</p> : null}
            {alertsData ? <AlertsDetail data={alertsData} /> : null}
          </section>
          <section className="panel">
            <div className="section-heading-row">
              <h3>流量统计 Flow Counts</h3>
              <button
                disabled={!selectedRunId || flowCountsLoading}
                type="button"
                onClick={() => selectedRunId && loadFlowCounts(selectedRunId)}
              >
                刷新 Refresh
              </button>
            </div>
            {flowCountsLoading ? <p className="muted">正在加载 flow_counts.json...</p> : null}
            {flowCountsError ? <p>{flowCountsError}</p> : null}
            {flowCountsData ? <FlowCountsDetail data={flowCountsData} /> : null}
          </section>
          <section className="panel">
            <div className="section-heading-row">
              <h3>区域统计 Zone Statistics</h3>
              <button
                disabled={!selectedRunId || zoneStatisticsLoading}
                type="button"
                onClick={() => selectedRunId && loadZoneStatistics(selectedRunId)}
              >
                刷新 Refresh
              </button>
            </div>
            {zoneStatisticsLoading ? <p className="muted">正在加载 zone_statistics.json...</p> : null}
            {zoneStatisticsError ? <p>{zoneStatisticsError}</p> : null}
            {zoneStatisticsData ? <ZoneStatisticsDetail data={zoneStatisticsData} /> : null}
          </section>
          <section className="panel">
            <h3>检测摘要 Detection Summary</h3>
            {detectionsLoading ? <p className="muted">正在加载检测结果...</p> : null}
            {detectionsError ? <p>{detectionsError}</p> : null}
            {detections ? (
              <>
              <p>
                {formatValue(detections.summary.total_frames_processed, "0")} 帧 frames ·{" "}
                {formatValue(detections.summary.total_detections, "0")} 检测 detections
              </p>
              <h3>帧结果 Frame Results</h3>
              <table>
                <thead>
                  <tr>
                    <th>帧 Frame</th>
                    <th>时间戳 Timestamp</th>
                    <th>检测数 Detections</th>
                  </tr>
                </thead>
                <tbody>
                  {detections.frames.map((frame) => (
                    <tr key={frame.frame_index}>
                      <td>{frame.frame_index}</td>
                      <td>{frame.timestamp_ms ?? 0} ms</td>
                      <td>{frame.detections.length}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </>
            ) : null}
          </section>
          <section className="panel">
            <h3>跟踪摘要 Tracking Summary</h3>
            {tracksLoading ? <p className="muted">正在加载跟踪结果...</p> : null}
            {tracksError ? <p>{tracksError}</p> : null}
            {tracks ? (
              <>
              <p>
                {formatValue(tracks.summary.total_frames_processed, "0")} 帧 frames ·{" "}
                {formatValue(tracks.summary.total_tracks, "0")} 跟踪行 track rows ·{" "}
                {formatValue(tracks.summary.unique_track_ids, "0")} 唯一 ID unique IDs
              </p>
              <h3>跟踪结果 Track Results</h3>
              <table>
                <thead>
                  <tr>
                    <th>帧 Frame</th>
                    <th>Track ID</th>
                    <th>类别 Class</th>
                    <th>状态 State</th>
                  </tr>
                </thead>
                <tbody>
                  {tracks.rows.slice(0, 20).map((track, index) => (
                    <tr key={`${track.frame_index}-${track.track_id}-${index}`}>
                      <td>{track.frame_index}</td>
                      <td>{track.track_id}</td>
                      <td>{track.class_name}</td>
                      <td>{track.state}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </>
            ) : null}
          </section>
        </div>
      </div>
    </>
  );
}

function RunSummaryPanel({ run }: { run: AnalysisRunSummary }) {
  return (
    <dl className="detail-grid">
      <div>
        <dt>run_id</dt>
        <dd>{formatValue(getRunId(run))}</dd>
      </div>
      <div>
        <dt>video_id</dt>
        <dd>{formatValue(run.video_id)}</dd>
      </div>
      <div>
        <dt>状态 status</dt>
        <dd>{formatValue(run.status)}</dd>
      </div>
      <div>
        <dt>source</dt>
        <dd>{formatValue(run.source)}</dd>
      </div>
      <div>
        <dt>result_dir</dt>
        <dd>{formatValue(run.result_dir)}</dd>
      </div>
      <div>
        <dt>created_at</dt>
        <dd>{formatValue(run.created_at)}</dd>
      </div>
      <div>
        <dt>updated_at</dt>
        <dd>{formatValue(run.updated_at)}</dd>
      </div>
      <div>
        <dt>started_at</dt>
        <dd>{formatValue(run.started_at)}</dd>
      </div>
      <div>
        <dt>finished_at</dt>
        <dd>{formatValue(run.finished_at)}</dd>
      </div>
    </dl>
  );
}

function IndexStatusPanel({
  manifestPayload,
  run
}: {
  manifestPayload: Record<string, unknown> | null;
  run: AnalysisRunSummary;
}) {
  return (
    <>
      <table>
        <thead>
          <tr>
            <th>Index</th>
            <th>状态 Status</th>
            <th>可用 Available</th>
            <th>路径 Path</th>
            <th>Schema</th>
            <th>错误 Error</th>
          </tr>
        </thead>
        <tbody>
          <ArtifactAvailabilityRow label="metadata" value={run.metadata} />
          <ArtifactAvailabilityRow label="manifest" value={run.manifest} />
          <ArtifactAvailabilityRow label="artifact_index" value={run.artifact_index} />
        </tbody>
      </table>
      <p className="muted">
        Manifest endpoint schema: {formatValue(manifestPayload?.schema_version)}
      </p>
    </>
  );
}

function ArtifactAvailabilityRow({
  label,
  value
}: {
  label: string;
  value?: ArtifactAvailability;
}) {
  const status = value?.status || "missing";
  return (
    <tr>
      <td>{label}</td>
      <td>
        <span className={`status-pill status-${status}`}>{status}</span>
      </td>
      <td>{formatValue(value?.available)}</td>
      <td>{formatValue(value?.path)}</td>
      <td>{formatValue(value?.schema_version)}</td>
      <td>{formatValue(value?.error)}</td>
    </tr>
  );
}

function ArtifactSummaryTable({ artifactSummary }: { artifactSummary?: ArtifactSummary }) {
  const rows = artifactSummary ? Object.entries(artifactSummary).sort(([left], [right]) => left.localeCompare(right)) : [];
  if (rows.length === 0) {
    return <p className="muted">暂无产物摘要。</p>;
  }

  return (
    <table>
      <thead>
        <tr>
          <th>产物键 Artifact key</th>
          <th>状态 Status</th>
          <th>路径 Path</th>
          <th>记录数 Record count</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(([key, item]) => (
          <tr key={key}>
            <td>{key}</td>
            <td>
              <span className={`status-pill status-${item.status}`}>{item.status}</span>
            </td>
            <td>{formatValue(item.path)}</td>
            <td>{formatValue(item.record_count)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function VisualArtifactsPanel({ artifactSummary }: { artifactSummary?: ArtifactSummary }) {
  const keyframes = artifactSummary?.keyframes;
  const keyframesIndex = artifactSummary?.keyframes_index;
  const annotatedVideo = artifactSummary?.annotated_video;

  if (!keyframes && !keyframesIndex && !annotatedVideo) {
    return <p className="muted">暂无可视化产物状态。</p>;
  }

  return (
    <table>
      <thead>
        <tr>
          <th>产物 Artifact</th>
          <th>状态 Status</th>
          <th>数量 Count</th>
          <th>路径 Path</th>
        </tr>
      </thead>
      <tbody>
        <VisualArtifactRow label="keyframes" value={keyframes} />
        <VisualArtifactRow label="keyframes_index" value={keyframesIndex} />
        <VisualArtifactRow label="annotated_video" value={annotatedVideo} />
      </tbody>
    </table>
  );
}

function VisualArtifactRow({
  label,
  value
}: {
  label: string;
  value?: ArtifactSummaryItem;
}) {
  const status = value?.status || "missing";
  return (
    <tr>
      <td>{label}</td>
      <td>
        <span className={`status-pill status-${status}`}>{status}</span>
      </td>
      <td>{formatValue(value?.record_count)}</td>
      <td>{formatValue(value?.path)}</td>
    </tr>
  );
}

function TrajectoryDetail({ data }: { data: TrajectoryPointsResponse }) {
  const rowPreview = data.rows.slice(0, 20);
  const framePreview = data.frames.slice(0, 10);
  const pointCount = data.frames.reduce(
    (total, frame) => total + frame.trajectory_points.length,
    0
  );
  const hasFilter = data.track_id !== undefined && data.track_id !== null;
  const hasNoMatches = hasFilter && data.rows.length === 0 && pointCount === 0;

  return (
    <>
      <h3>轨迹摘要 Trajectory Summary</h3>
      <p>
        {formatValue(data.summary.total_frames_processed ?? 0)} 帧 frames ·{" "}
        {formatValue(data.summary.total_trajectory_points ?? 0)} 轨迹点 trajectory points ·{" "}
        {formatValue(data.summary.unique_track_ids ?? 0)} 唯一 ID unique IDs · 平均长度 avg length{" "}
        {formatValue(data.summary.avg_track_length)} · 最大长度 max length{" "}
        {formatValue(data.summary.max_track_length)} · 平均速度 avg speed{" "}
        {formatValue(data.summary.avg_speed_px_per_second)}
      </p>
      {hasNoMatches ? <p className="muted">没有匹配的 trajectory points</p> : null}
      <h3>轨迹行 Trajectory Rows</h3>
      {rowPreview.length === 0 ? (
        <p className="muted">暂无 trajectory rows</p>
      ) : (
        <table>
          <thead>
            <tr>
              {trajectoryColumns.map((column) => (
                <th key={String(column)}>{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rowPreview.map((row, index) => (
              <tr key={`${row.frame_index}-${row.track_id}-${index}`}>
                {trajectoryColumns.map((column) => (
                  <td key={String(column)}>{formatValue(row[column])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <h3>轨迹帧 Trajectory Frames</h3>
      {framePreview.length === 0 ? (
        <p className="muted">暂无 trajectory frames</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>帧 Frame</th>
              <th>时间戳 Timestamp</th>
              <th>点数 Point count</th>
              <th>Track IDs</th>
            </tr>
          </thead>
          <tbody>
            {framePreview.map((frame, index) => (
              <tr key={`${frame.frame_index}-${index}`}>
                <td>{formatValue(frame.frame_index)}</td>
                <td>{formatValue(frame.timestamp_ms)}</td>
                <td>{frame.trajectory_points.length}</td>
                <td>{formatTrackIds(frame)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}

function EventsDetail({
  data,
  onOpenReview,
  onSelectEvent,
  selectedEventId
}: {
  data: EventsResponse;
  onOpenReview?: (href: string) => void;
  onSelectEvent?: (eventId: string, event: EventRecord) => void;
  selectedEventId?: string | null;
}) {
  const evidencePreview = data.event_evidence.slice(0, 20);
  const executionPreview = data.rule_executions.slice(0, 20);

  return (
    <>
      <h3>事件摘要 Event Summary</h3>
      <p>
        {formatValue(data.summary.total_events ?? 0)} 事件 events ·{" "}
        {formatValue(data.summary.unique_track_ids ?? 0)} 唯一 ID unique IDs · 首个 first{" "}
        {formatValue(data.summary.first_event_time_ms)} · 最后 last{" "}
        {formatValue(data.summary.last_event_time_ms)}
      </p>
      <p className="muted">
        types {formatCountMap(data.summary.per_event_type_counts)} · severity{" "}
        {formatCountMap(data.summary.per_severity_counts)} · status{" "}
        {formatCountMap(data.summary.per_status_counts)}
      </p>
      <h3>事件 Events</h3>
      <EventTable
        buildReviewHref={(event) => {
          const eventId = normalizeOptionalRecordValue(event.event_id);
          return eventId ? buildReviewLink(data.run_id, eventId) : null;
        }}
        events={data.events}
        maxRows={20}
        onOpenReview={onOpenReview}
        onSelectEvent={onSelectEvent}
        selectedEventId={selectedEventId}
      />
      <h3>事件证据 Event Evidence</h3>
      {evidencePreview.length === 0 ? (
        <p className="muted">暂无 event evidence</p>
      ) : (
        <RecordTable columns={evidenceColumns} rows={evidencePreview} />
      )}
      <h3>规则执行 Rule Executions</h3>
      {executionPreview.length === 0 ? (
        <p className="muted">暂无 rule executions</p>
      ) : (
        <RecordTable columns={ruleExecutionColumns} rows={executionPreview} />
      )}
    </>
  );
}

function normalizeOptionalRecordValue(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function AlertsDetail({ data }: { data: AlertsResponse }) {
  const alertPreview = data.alerts.slice(0, 20);

  return (
    <>
      <h3>告警摘要 Alert Summary</h3>
      <p>
        {formatValue(data.summary.total_alerts ?? 0)} 告警 alerts ·{" "}
        {formatValue(data.summary.unique_event_ids ?? 0)} 事件 events ·{" "}
        {formatValue(data.summary.unique_track_ids ?? 0)} 唯一 ID unique IDs · 首个 first{" "}
        {formatValue(data.summary.first_alert_time_ms)} · 最后 last{" "}
        {formatValue(data.summary.last_alert_time_ms)}
      </p>
      <p className="muted">
        types {formatCountMap(data.summary.per_alert_type_counts)} · level{" "}
        {formatCountMap(data.summary.per_level_counts)} · status{" "}
        {formatCountMap(data.summary.per_status_counts)}
      </p>
      <h3>告警 Alerts</h3>
      {alertPreview.length === 0 ? (
        <p className="muted">暂无告警。事件触发后会在这里显示。</p>
      ) : (
        <RecordTable columns={alertColumns} rows={alertPreview} />
      )}
    </>
  );
}

function FlowCountsDetail({ data }: { data: FlowCountsArtifact }) {
  const records = data.records ?? [];
  const windows = data.windows ?? [];

  return (
    <>
      <p>
        {formatValue(data.summary?.total_count ?? 0)} 总计 total ·{" "}
        {formatValue(data.summary?.vehicle_count ?? 0)} 车辆 vehicles ·{" "}
        {formatValue(data.summary?.person_count ?? 0)} 行人 people · {records.length} 记录 records ·{" "}
        {windows.length} 窗口 windows
      </p>
      <p className="muted">
        schema {formatValue(data.schema_version)} · window {formatValue(data.window_ms)} ms
      </p>
      <h3>流量窗口 Flow Windows</h3>
      {windows.length === 0 ? (
        <p className="muted">暂无 flow windows</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>窗口 Window</th>
              <th>区域 Zone</th>
              <th>线 Line</th>
              <th>类别 Class</th>
              <th>方向 Direction</th>
              <th>总计 Total</th>
            </tr>
          </thead>
          <tbody>
            {windows.slice(0, 20).map((window, index) => (
              <tr key={`${window.time_window_start_ms}-${window.zone_id}-${index}`}>
                <td>
                  {formatValue(window.time_window_start_ms)} -{" "}
                  {formatValue(window.time_window_end_ms)}
                </td>
                <td>{formatValue(window.zone_id)}</td>
                <td>{formatValue(window.counting_line_id)}</td>
                <td>{formatValue(window.class_name)}</td>
                <td>{formatValue(window.direction)}</td>
                <td>{formatValue(window.total_count)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <h3>流量记录 Flow Records</h3>
      {records.length === 0 ? (
        <p className="muted">暂无 flow records</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>事件 Event</th>
              <th>Track</th>
              <th>区域 Zone</th>
              <th>线 Line</th>
              <th>类别 Class</th>
              <th>方向 Direction</th>
            </tr>
          </thead>
          <tbody>
            {records.slice(0, 20).map((record, index) => (
              <tr key={`${record.event_id}-${record.track_id}-${index}`}>
                <td>{formatValue(record.event_id)}</td>
                <td>{formatValue(record.track_id)}</td>
                <td>{formatValue(record.zone_id)}</td>
                <td>{formatValue(record.counting_line_id)}</td>
                <td>{formatValue(record.class_name)}</td>
                <td>{formatValue(record.direction)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}

function ZoneStatisticsDetail({ data }: { data: ZoneStatisticsArtifact }) {
  const windows = data.windows ?? [];
  const congestionEvents = data.congestion_events ?? [];

  return (
    <>
      <p>
        {formatValue(data.summary?.zone_count ?? 0)} 区域 zones ·{" "}
        {formatValue(data.summary?.total_windows ?? 0)} 窗口 windows ·{" "}
        {formatValue(data.summary?.congestion_event_count ?? 0)} 拥堵事件 congestion events ·{" "}
        {windows.length} 窗口行 window rows · {congestionEvents.length} 事件行 event rows
      </p>
      <p className="muted">
        schema {formatValue(data.schema_version)} · window {formatValue(data.window_ms)} ms
      </p>
      <h3>区域窗口 Zone Windows</h3>
      {windows.length === 0 ? (
        <p className="muted">暂无 zone windows</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>窗口 Window</th>
              <th>区域 Zone</th>
              <th>车辆 Vehicles</th>
              <th>行人 People</th>
              <th>占用 Occupancy</th>
              <th>平均速度 Avg speed</th>
            </tr>
          </thead>
          <tbody>
            {windows.slice(0, 20).map((window, index) => (
              <tr key={`${window.time_window_start_ms}-${window.zone_id}-${index}`}>
                <td>
                  {formatValue(window.time_window_start_ms)} -{" "}
                  {formatValue(window.time_window_end_ms)}
                </td>
                <td>{formatValue(window.zone_id)}</td>
                <td>{formatValue(window.vehicle_count)}</td>
                <td>{formatValue(window.person_count)}</td>
                <td>{formatValue(window.occupancy_count)}</td>
                <td>{formatValue(window.avg_speed_px_per_frame)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <h3>拥堵事件 Congestion Events</h3>
      {congestionEvents.length === 0 ? (
        <p className="muted">暂无 congestion events</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>事件 Event</th>
              <th>区域 Zone</th>
              <th>帧 Frame</th>
              <th>时间戳 Timestamp</th>
              <th>车辆 Vehicles</th>
              <th>平均速度 Avg speed</th>
            </tr>
          </thead>
          <tbody>
            {congestionEvents.slice(0, 20).map((event, index) => (
              <tr key={`${event.event_id}-${index}`}>
                <td>{formatValue(event.event_id)}</td>
                <td>{formatValue(event.zone_id)}</td>
                <td>{formatValue(event.frame_index)}</td>
                <td>{formatValue(event.timestamp_ms)}</td>
                <td>{formatValue(event.vehicle_count)}</td>
                <td>{formatValue(event.avg_speed_px_per_frame)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}

function RecordTable({
  columns,
  rows
}: {
  columns: readonly string[];
  rows: Array<AlertRecord | EventRecord | EventEvidenceRecord | RuleExecutionRecord>;
}) {
  return (
    <table>
      <thead>
        <tr>
          {columns.map((column) => (
            <th key={column}>{column}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, index) => (
          <tr
            key={`${formatValue(row.alert_id)}-${formatValue(row.event_id)}-${formatValue(row.rule_id)}-${index}`}
          >
            {columns.map((column) => (
              <td key={column}>{formatValue(row[column])}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function parseTrackIdFilter(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }

  const parsed = Number(trimmed);
  if (!Number.isInteger(parsed)) {
    return null;
  }
  return parsed;
}

function normalizeOptionalString(value: string): string | null {
  const trimmed = value.trim();
  return trimmed || null;
}

function normalizeVideoUrl(value: string | undefined): string | null {
  if (!value) {
    return null;
  }
  if (value.startsWith("http://") || value.startsWith("https://") || value.startsWith("/")) {
    return value;
  }
  return null;
}

function clampInteger(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) {
    return min;
  }
  return Math.min(max, Math.max(min, Math.trunc(value)));
}

function formatCountMap(value: Record<string, number> | undefined): string {
  if (!value || Object.keys(value).length === 0) {
    return "-";
  }
  return Object.entries(value)
    .map(([key, count]) => `${key}:${count}`)
    .join(", ");
}

function formatTrackIds(frame: TrajectoryFrame): string {
  const ids = frame.trajectory_points
    .map((point) => point.track_id)
    .filter((trackId): trackId is number => trackId !== undefined && trackId !== null);
  if (ids.length === 0) {
    return "-";
  }
  return Array.from(new Set(ids)).join(", ");
}
