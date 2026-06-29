import { useEffect, useState, type ReactNode } from "react";

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

const TIMELINE_PREVIEW_LIMIT = 7;
const TABLE_PREVIEW_LIMIT = 10;

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
  const events = eventsData?.events ?? [];
  const alerts = alertsData?.alerts ?? [];
  const eventEvidenceCount = eventsData?.event_evidence.length ?? 0;
  const ruleExecutions = eventsData?.rule_executions ?? [];
  const matchedRuleExecutions = countRowsByStatus(ruleExecutions, "matched");
  const skippedRuleExecutions = countRowsByStatus(ruleExecutions, "skipped");
  const artifactSummary = runSummary?.artifact_summary;

  return (
    <div className="analysis-detail-page">
      <header className="page-header">
        <div>
          <h2>分析详情</h2>
          <p>查看检测、跟踪、轨迹、事件证据和分析产物。</p>
        </div>
      </header>
      <div className="page-grid-2 analysis-hero-grid">
        <VideoPlayerWithOverlay
          currentTimeMs={currentTimeMs}
          detections={overlayData.detections}
          height={overlaySize.height}
          onSeek={setCurrentTimeMs}
          selectedEventId={selectedEventId}
          selectedTrackId={overlayData.selectedTrackId}
          selectedZoneId={overlayData.selectedZoneId}
          title="视频叠加"
          tracks={overlayData.tracks}
          trajectoryPoints={overlayData.trajectoryFrames}
          videoUrl={videoUrl}
          width={overlaySize.width}
          zones={overlayData.zones}
        />
        <div className="analysis-timeline-column card-fill">
          <EventTimeline
            displayLimit={TIMELINE_PREVIEW_LIMIT}
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
        </div>
      </div>
      <section className="summary-grid analysis-summary-grid">
        <SummaryCard title="叠加数据">
          {zonesError ? <p className="alert-box error">{zonesError}</p> : null}
          {zonesLoading ? <p className="muted">正在加载区域...</p> : null}
          <SummaryMetric label="检测帧" value={overlayData.detections.length} />
          <SummaryMetric label="跟踪帧" value={overlayData.tracks.length} />
          <SummaryMetric label="轨迹帧" value={overlayData.trajectoryFrames.length} />
          <SummaryMetric label="区域数" value={overlayData.zones.length} />
        </SummaryCard>
        <SummaryCard title="任务摘要">
          <label className="stacked-control">
            分析任务 ID
            <select
              value={selectedRunId}
              onChange={(event) => setSelectedRunId(event.target.value)}
            >
              <option value="">未选择分析任务</option>
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
          {runsError ? <p className="alert-box error">{runsError}</p> : null}
          {runSummaryError ? <p className="alert-box error">{runSummaryError}</p> : null}
          {runs.length === 0 && !runsLoading ? (
            <p className="empty-state">暂无分析任务。请先在视频中心上传视频并启动分析。</p>
          ) : null}
          <SummaryMetric label="run_id" value={runSummary ? getRunId(runSummary) : selectedRunId || "-"} />
          <SummaryMetric label="状态" value={runSummaryLoading ? "加载中" : runSummary?.status} />
          <SummaryMetric label="来源" value={runSummary?.source} />
        </SummaryCard>
        <SummaryCard title="轨迹摘要">
          {trajectoryLoading ? <p className="muted">正在加载轨迹...</p> : null}
          {trajectoryError ? <p className="alert-box error">{trajectoryError}</p> : null}
          <SummaryMetric label="帧数" value={trajectoryData?.summary.total_frames_processed} />
          <SummaryMetric label="轨迹点" value={trajectoryData?.summary.total_trajectory_points} />
          <SummaryMetric label="唯一 ID" value={trajectoryData?.summary.unique_track_ids} />
        </SummaryCard>
        <SummaryCard title="事件摘要">
          {eventsLoading ? <p className="muted">正在加载事件...</p> : null}
          {eventsError ? <p className="alert-box error">{eventsError}</p> : null}
          <SummaryMetric label="事件数" value={eventsData?.summary.total_events ?? events.length} />
          <SummaryMetric label="主要类型" value={topCountLabel(eventsData?.summary.per_event_type_counts)} />
          <SummaryMetric label="状态" value={formatCountMap(eventsData?.summary.per_status_counts)} />
        </SummaryCard>
        <SummaryCard title="告警摘要">
          {alertsLoading ? <p className="muted">正在加载告警...</p> : null}
          {alertsError ? <p className="alert-box error">{alertsError}</p> : null}
          <SummaryMetric label="告警数" value={alertsData?.summary.total_alerts ?? alerts.length} />
          <SummaryMetric label="级别" value={formatCountMap(alertsData?.summary.per_level_counts)} />
          <SummaryMetric label="状态" value={formatCountMap(alertsData?.summary.per_status_counts)} />
        </SummaryCard>
        <SummaryCard title="产物摘要">
          <SummaryMetric label="标注视频" value={artifactStatus(artifactSummary, "annotated_video")} />
          <SummaryMetric label="关键帧" value={artifactRecordCount(artifactSummary, "keyframes")} />
          <SummaryMetric label="报告产物" value={artifactSummaryLabel(artifactSummary)} />
        </SummaryCard>
      </section>

      <section className="analysis-business-results">
        <section className="panel table-section table-card">
          <div className="section-heading-row">
            <h3>事件列表</h3>
            <span className="status-pill">{events.length} 个事件</span>
          </div>
          {events.length === 0 ? (
            <p className="muted">暂无事件。请先运行一次视频分析。</p>
          ) : (
            <>
              <EventTable
                buildReviewHref={(event) => {
                  const eventId = normalizeOptionalRecordValue(event.event_id);
                  return eventId ? buildReviewLink(eventsData?.run_id ?? selectedRunId, eventId) : null;
                }}
                events={events}
                maxRows={TABLE_PREVIEW_LIMIT}
                onOpenReview={onOpenReview}
                onSelectEvent={(eventId, event) => {
                  setSelectedEventId(eventId);
                  setCurrentTimeMs(getEventSeekTimeMs(event));
                }}
                selectedEventId={selectedEventId}
              />
              <PreviewNotice total={events.length} limit={TABLE_PREVIEW_LIMIT} />
            </>
          )}
        </section>

        <section className="panel table-section table-card">
          <div className="section-heading-row">
            <h3>告警列表</h3>
            <span className="status-pill">{alerts.length} 个告警</span>
          </div>
          <div className="toolbar compact">
            <button disabled={!selectedRunId || alertsLoading} type="button" onClick={handleGenerateAlerts}>
              从事件生成告警
            </button>
            <button disabled={!selectedRunId || alertsLoading} type="button" onClick={handleAlertsRefresh}>
              刷新告警
            </button>
          </div>
          {alerts.length === 0 ? (
            <p className="muted">暂无告警。事件触发后会在这里显示。</p>
          ) : (
            <>
              <RecordTable
                caption="告警列表"
                columns={alertColumns}
                rows={alerts.slice(0, TABLE_PREVIEW_LIMIT)}
              />
              <PreviewNotice total={alerts.length} limit={TABLE_PREVIEW_LIMIT} />
            </>
          )}
        </section>

        <section className="panel evidence-overview-card">
          <div className="section-heading-row">
            <h3>关键证据摘要</h3>
            <span className="status-pill">{eventEvidenceCount} 条证据</span>
          </div>
          <div className="summary-grid">
            <SummaryMetric label="事件证据" value={eventEvidenceCount} />
            <SummaryMetric label="规则执行" value={ruleExecutions.length} />
            <SummaryMetric label="matched" value={matchedRuleExecutions} />
            <SummaryMetric label="skipped" value={skippedRuleExecutions} />
          </div>
        </section>
      </section>

      <section className="analysis-advanced-sections">
        <CollapsibleSection title="高级明细">
          <div className="analysis-advanced-grid">
            <section className="advanced-detail-block">
              <h3>完整任务摘要</h3>
              {runSummary ? <RunSummaryPanel run={runSummary} /> : <p className="muted">请选择一个分析任务。</p>}
            </section>
            <section className="advanced-detail-block table-section">
              <h3>索引状态</h3>
              {manifestLoading ? <p className="muted">正在加载 manifest...</p> : null}
              {manifestError ? <p className="alert-box error">{manifestError}</p> : null}
              {runSummary ? (
                <IndexStatusPanel manifestPayload={manifestPayload} run={runSummary} />
              ) : (
                <p className="muted">请选择一个分析任务，查看 metadata、manifest 和 artifact index。</p>
              )}
            </section>
          </div>
        </CollapsibleSection>

        <CollapsibleSection title="原始产物">
          <div className="analysis-advanced-grid">
            <section className="advanced-detail-block table-section">
              <h3>完整产物摘要</h3>
              <ArtifactSummaryTable artifactSummary={artifactSummary} />
            </section>
            <section className="advanced-detail-block table-section">
              <h3>可视化产物明细</h3>
              <VisualArtifactsPanel artifactSummary={artifactSummary} />
            </section>
          </div>
        </CollapsibleSection>

        <CollapsibleSection title="轨迹明细">
          <section className="advanced-detail-block table-section">
            <h3>轨迹查询</h3>
            <div className="toolbar">
              <label>
                条数
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
                应用 / 刷新
              </button>
            </div>
            {trajectoryData ? <TrajectoryDetail data={trajectoryData} /> : null}
          </section>
        </CollapsibleSection>

        <CollapsibleSection title="事件证据与规则执行">
          <section className="advanced-detail-block table-section">
            <h3>事件查询</h3>
            <div className="toolbar">
              <label>
                条数
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
                事件类型
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
                应用 / 刷新
              </button>
            </div>
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
        </CollapsibleSection>

        <CollapsibleSection title="告警明细">
          <section className="advanced-detail-block table-section">
            <h3>告警查询</h3>
            <div className="toolbar">
              <label>
                条数
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
                状态
                <input
                  placeholder="all"
                  value={alertStatusFilter}
                  onChange={(event) => setAlertStatusFilter(event.target.value)}
                />
              </label>
              <label>
                级别
                <input
                  placeholder="all"
                  value={alertLevelFilter}
                  onChange={(event) => setAlertLevelFilter(event.target.value)}
                />
              </label>
              <label>
                事件类型
                <input
                  placeholder="all"
                  value={alertEventTypeFilter}
                  onChange={(event) => setAlertEventTypeFilter(event.target.value)}
                />
              </label>
              <button disabled={!selectedRunId || alertsLoading} type="button" onClick={handleAlertsRefresh}>
                刷新告警
              </button>
            </div>
            {alertsData ? <AlertsDetail data={alertsData} /> : null}
          </section>
        </CollapsibleSection>

        <CollapsibleSection title="流量与区域统计">
          <div className="analysis-advanced-grid">
            <section className="advanced-detail-block table-section">
              <div className="section-heading-row">
                <h3>流量统计</h3>
                <button
                  disabled={!selectedRunId || flowCountsLoading}
                  type="button"
                  onClick={() => selectedRunId && loadFlowCounts(selectedRunId)}
                >
                  刷新
                </button>
              </div>
              {flowCountsLoading ? <p className="muted">正在加载 flow_counts.json...</p> : null}
              {flowCountsError ? <p className="alert-box error">{flowCountsError}</p> : null}
              {flowCountsData ? <FlowCountsDetail data={flowCountsData} /> : null}
            </section>
            <section className="advanced-detail-block table-section">
              <div className="section-heading-row">
                <h3>区域统计</h3>
                <button
                  disabled={!selectedRunId || zoneStatisticsLoading}
                  type="button"
                  onClick={() => selectedRunId && loadZoneStatistics(selectedRunId)}
                >
                  刷新
                </button>
              </div>
              {zoneStatisticsLoading ? <p className="muted">正在加载 zone_statistics.json...</p> : null}
              {zoneStatisticsError ? <p className="alert-box error">{zoneStatisticsError}</p> : null}
              {zoneStatisticsData ? <ZoneStatisticsDetail data={zoneStatisticsData} /> : null}
            </section>
          </div>
        </CollapsibleSection>

        <CollapsibleSection title="检测与跟踪明细">
          <div className="analysis-advanced-grid">
            <section className="advanced-detail-block table-section">
              <h3>检测摘要</h3>
              {detectionsLoading ? <p className="muted">正在加载检测结果...</p> : null}
              {detectionsError ? <p className="alert-box error">{detectionsError}</p> : null}
              {detections ? <DetectionsDetail data={detections} /> : null}
            </section>
            <section className="advanced-detail-block table-section">
              <h3>跟踪摘要</h3>
              {tracksLoading ? <p className="muted">正在加载跟踪结果...</p> : null}
              {tracksError ? <p className="alert-box error">{tracksError}</p> : null}
              {tracks ? <TracksDetail data={tracks} /> : null}
            </section>
          </div>
        </CollapsibleSection>
      </section>
    </div>
  );
}

function SummaryCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="panel summary-card">
      <h3>{title}</h3>
      <div className="summary-card-body">{children}</div>
    </section>
  );
}

function SummaryMetric({
  label,
  value
}: {
  label: string;
  value: string | number | null | undefined;
}) {
  const displayValue = formatValue(value);
  return (
    <div className="summary-metric" title={displayValue}>
      <span className="summary-metric-label">{label}</span>
      <span className="summary-metric-value">{displayValue}</span>
    </div>
  );
}

function CollapsibleSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <details className="collapsible-section">
      <summary>{title}</summary>
      <div className="collapsible-body">{children}</div>
    </details>
  );
}

function PreviewNotice({ total, limit }: { total: number; limit: number }) {
  if (total <= limit) {
    return null;
  }
  return (
    <p className="muted preview-notice">
      仅展示前 {limit} 条，完整数据请展开高级明细或查看导出文件。
    </p>
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
        <dt>状态</dt>
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
        <caption className="sr-only">分析任务索引状态</caption>
        <thead>
          <tr>
            <th scope="col">Index</th>
            <th scope="col">状态</th>
            <th scope="col">可用</th>
            <th scope="col">路径</th>
            <th scope="col">Schema</th>
            <th scope="col">错误</th>
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
      <td className="cell-path" title={formatValue(value?.path)}>
        {formatValue(value?.path)}
      </td>
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
      <caption className="sr-only">完整产物摘要</caption>
      <thead>
        <tr>
          <th scope="col">产物键</th>
          <th scope="col">状态</th>
          <th scope="col">路径</th>
          <th scope="col">记录数</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(([key, item]) => (
          <tr key={key}>
            <td>{key}</td>
            <td>
              <span className={`status-pill status-${item.status}`}>{item.status}</span>
            </td>
            <td className="cell-path" title={formatValue(item.path)}>
              {formatValue(item.path)}
            </td>
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
      <caption className="sr-only">可视化产物明细</caption>
      <thead>
        <tr>
          <th scope="col">产物</th>
          <th scope="col">状态</th>
          <th scope="col">数量</th>
          <th scope="col">路径</th>
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
      <td className="cell-path" title={formatValue(value?.path)}>
        {formatValue(value?.path)}
      </td>
    </tr>
  );
}

function DetectionsDetail({ data }: { data: AnalysisRunDetections }) {
  const framePreview = data.frames.slice(0, TABLE_PREVIEW_LIMIT);
  return (
    <>
      <p>
        {formatValue(data.summary.total_frames_processed, "0")} 帧 ·{" "}
        {formatValue(data.summary.total_detections, "0")} 检测
      </p>
      <h3>检测帧结果</h3>
      {framePreview.length === 0 ? (
        <p className="muted">暂无检测帧。</p>
      ) : (
        <>
          <table>
            <caption className="sr-only">检测帧结果</caption>
            <thead>
              <tr>
                <th scope="col">帧</th>
                <th scope="col">时间戳</th>
                <th scope="col">检测数</th>
              </tr>
            </thead>
            <tbody>
              {framePreview.map((frame) => (
                <tr key={frame.frame_index}>
                  <td>{frame.frame_index}</td>
                  <td>{frame.timestamp_ms ?? 0} ms</td>
                  <td>{frame.detections.length}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <PreviewNotice total={data.frames.length} limit={TABLE_PREVIEW_LIMIT} />
        </>
      )}
    </>
  );
}

function TracksDetail({ data }: { data: AnalysisRunTracks }) {
  const rowPreview = data.rows.slice(0, TABLE_PREVIEW_LIMIT);
  return (
    <>
      <p>
        {formatValue(data.summary.total_frames_processed, "0")} 帧 ·{" "}
        {formatValue(data.summary.total_tracks, "0")} 跟踪行 ·{" "}
        {formatValue(data.summary.unique_track_ids, "0")} 唯一 ID
      </p>
      <h3>跟踪结果</h3>
      {rowPreview.length === 0 ? (
        <p className="muted">暂无跟踪结果。</p>
      ) : (
        <>
          <table>
            <caption className="sr-only">跟踪结果</caption>
            <thead>
              <tr>
                <th scope="col">帧</th>
                <th scope="col">Track ID</th>
                <th scope="col">类别</th>
                <th scope="col">状态</th>
              </tr>
            </thead>
            <tbody>
              {rowPreview.map((track, index) => (
                <tr key={`${track.frame_index}-${track.track_id}-${index}`}>
                  <td>{track.frame_index}</td>
                  <td className="cell-id" title={formatValue(track.track_id)}>
                    {track.track_id}
                  </td>
                  <td>{track.class_name}</td>
                  <td>{track.state}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <PreviewNotice total={data.rows.length} limit={TABLE_PREVIEW_LIMIT} />
        </>
      )}
    </>
  );
}

function TrajectoryDetail({ data }: { data: TrajectoryPointsResponse }) {
  const rowPreview = data.rows.slice(0, TABLE_PREVIEW_LIMIT);
  const framePreview = data.frames.slice(0, TABLE_PREVIEW_LIMIT);
  const pointCount = data.frames.reduce(
    (total, frame) => total + frame.trajectory_points.length,
    0
  );
  const hasFilter = data.track_id !== undefined && data.track_id !== null;
  const hasNoMatches = hasFilter && data.rows.length === 0 && pointCount === 0;

  return (
    <>
      <h3>轨迹摘要</h3>
      <p>
        {formatValue(data.summary.total_frames_processed ?? 0)} 帧 ·{" "}
        {formatValue(data.summary.total_trajectory_points ?? 0)} 轨迹点 ·{" "}
        {formatValue(data.summary.unique_track_ids ?? 0)} 唯一 ID · 平均长度{" "}
        {formatValue(data.summary.avg_track_length)} · 最大长度{" "}
        {formatValue(data.summary.max_track_length)} · 平均速度{" "}
        {formatValue(data.summary.avg_speed_px_per_second)}
      </p>
      {hasNoMatches ? <p className="muted">没有匹配的 trajectory points</p> : null}
      <h3>轨迹行</h3>
      {rowPreview.length === 0 ? (
        <p className="muted">暂无 trajectory rows</p>
      ) : (
        <>
          <table>
            <caption className="sr-only">轨迹行</caption>
            <thead>
              <tr>
                {trajectoryColumns.map((column) => (
                  <th key={String(column)} scope="col">{column}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rowPreview.map((row, index) => (
                <tr key={`${row.frame_index}-${row.track_id}-${index}`}>
                  {trajectoryColumns.map((column) => (
                    <td
                      className={tableCellClassName(String(column))}
                      key={String(column)}
                      title={tableCellTitle(String(column), row[column])}
                    >
                      {formatValue(row[column])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <PreviewNotice total={data.rows.length} limit={TABLE_PREVIEW_LIMIT} />
        </>
      )}
      <h3>轨迹帧</h3>
      {framePreview.length === 0 ? (
        <p className="muted">暂无 trajectory frames</p>
      ) : (
        <>
          <table>
            <caption className="sr-only">轨迹帧</caption>
            <thead>
              <tr>
                <th scope="col">帧</th>
                <th scope="col">时间戳</th>
                <th scope="col">点数</th>
                <th scope="col">Track IDs</th>
              </tr>
            </thead>
            <tbody>
              {framePreview.map((frame, index) => (
                <tr key={`${frame.frame_index}-${index}`}>
                  <td>{formatValue(frame.frame_index)}</td>
                  <td>{formatValue(frame.timestamp_ms)}</td>
                  <td>{frame.trajectory_points.length}</td>
                  <td className="cell-id" title={formatTrackIds(frame)}>
                    {formatTrackIds(frame)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <PreviewNotice total={data.frames.length} limit={TABLE_PREVIEW_LIMIT} />
        </>
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
  const evidencePreview = data.event_evidence.slice(0, TABLE_PREVIEW_LIMIT);
  const executionPreview = data.rule_executions.slice(0, TABLE_PREVIEW_LIMIT);

  return (
    <>
      <h3>事件摘要</h3>
      <p>
        {formatValue(data.summary.total_events ?? 0)} 事件 ·{" "}
        {formatValue(data.summary.unique_track_ids ?? 0)} 唯一 ID · 首个{" "}
        {formatValue(data.summary.first_event_time_ms)} · 最后{" "}
        {formatValue(data.summary.last_event_time_ms)}
      </p>
      <p className="muted">
        类型 {formatCountMap(data.summary.per_event_type_counts)} · 严重程度{" "}
        {formatCountMap(data.summary.per_severity_counts)} · 状态{" "}
        {formatCountMap(data.summary.per_status_counts)}
      </p>
      <h3>事件</h3>
      <EventTable
        buildReviewHref={(event) => {
          const eventId = normalizeOptionalRecordValue(event.event_id);
          return eventId ? buildReviewLink(data.run_id, eventId) : null;
        }}
        events={data.events}
        maxRows={TABLE_PREVIEW_LIMIT}
        onOpenReview={onOpenReview}
        onSelectEvent={onSelectEvent}
        selectedEventId={selectedEventId}
      />
      <PreviewNotice total={data.events.length} limit={TABLE_PREVIEW_LIMIT} />
      <h3>事件证据</h3>
      {evidencePreview.length === 0 ? (
        <p className="muted">暂无 event evidence</p>
      ) : (
        <>
          <RecordTable caption="事件证据" columns={evidenceColumns} rows={evidencePreview} />
          <PreviewNotice total={data.event_evidence.length} limit={TABLE_PREVIEW_LIMIT} />
        </>
      )}
      <h3>规则执行</h3>
      {executionPreview.length === 0 ? (
        <p className="muted">暂无 rule executions</p>
      ) : (
        <>
          <RecordTable caption="规则执行" columns={ruleExecutionColumns} rows={executionPreview} />
          <PreviewNotice total={data.rule_executions.length} limit={TABLE_PREVIEW_LIMIT} />
        </>
      )}
    </>
  );
}

function normalizeOptionalRecordValue(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function AlertsDetail({ data }: { data: AlertsResponse }) {
  const alertPreview = data.alerts.slice(0, TABLE_PREVIEW_LIMIT);

  return (
    <>
      <h3>告警摘要</h3>
      <p>
        {formatValue(data.summary.total_alerts ?? 0)} 告警 ·{" "}
        {formatValue(data.summary.unique_event_ids ?? 0)} 事件 ·{" "}
        {formatValue(data.summary.unique_track_ids ?? 0)} 唯一 ID · 首个{" "}
        {formatValue(data.summary.first_alert_time_ms)} · 最后{" "}
        {formatValue(data.summary.last_alert_time_ms)}
      </p>
      <p className="muted">
        类型 {formatCountMap(data.summary.per_alert_type_counts)} · 级别{" "}
        {formatCountMap(data.summary.per_level_counts)} · 状态{" "}
        {formatCountMap(data.summary.per_status_counts)}
      </p>
      <h3>告警</h3>
      {alertPreview.length === 0 ? (
        <p className="muted">暂无告警。事件触发后会在这里显示。</p>
      ) : (
        <>
          <RecordTable caption="告警明细" columns={alertColumns} rows={alertPreview} />
          <PreviewNotice total={data.alerts.length} limit={TABLE_PREVIEW_LIMIT} />
        </>
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
        {formatValue(data.summary?.total_count ?? 0)} 总计 ·{" "}
        {formatValue(data.summary?.vehicle_count ?? 0)} 车辆 ·{" "}
        {formatValue(data.summary?.person_count ?? 0)} 行人 · {records.length} 记录 ·{" "}
        {windows.length} 窗口
      </p>
      <p className="muted">
        schema {formatValue(data.schema_version)} · window {formatValue(data.window_ms)} ms
      </p>
      <h3>流量窗口</h3>
      {windows.length === 0 ? (
        <p className="muted">暂无 flow windows</p>
      ) : (
        <>
          <table>
            <caption className="sr-only">流量窗口</caption>
            <thead>
              <tr>
                <th scope="col">窗口</th>
                <th scope="col">区域</th>
                <th scope="col">线</th>
                <th scope="col">类别</th>
                <th scope="col">方向</th>
                <th scope="col">总计</th>
              </tr>
            </thead>
            <tbody>
              {windows.slice(0, TABLE_PREVIEW_LIMIT).map((window, index) => (
                <tr key={`${window.time_window_start_ms}-${window.zone_id}-${index}`}>
                  <td>
                    {formatValue(window.time_window_start_ms)} -{" "}
                    {formatValue(window.time_window_end_ms)}
                  </td>
                  <td className="cell-id" title={formatValue(window.zone_id)}>
                    {formatValue(window.zone_id)}
                  </td>
                  <td className="cell-id" title={formatValue(window.counting_line_id)}>
                    {formatValue(window.counting_line_id)}
                  </td>
                  <td>{formatValue(window.class_name)}</td>
                  <td>{formatValue(window.direction)}</td>
                  <td>{formatValue(window.total_count)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <PreviewNotice total={windows.length} limit={TABLE_PREVIEW_LIMIT} />
        </>
      )}
      <h3>流量记录</h3>
      {records.length === 0 ? (
        <p className="muted">暂无 flow records</p>
      ) : (
        <>
          <table>
            <caption className="sr-only">流量记录</caption>
            <thead>
              <tr>
                <th scope="col">事件</th>
                <th scope="col">Track</th>
                <th scope="col">区域</th>
                <th scope="col">线</th>
                <th scope="col">类别</th>
                <th scope="col">方向</th>
              </tr>
            </thead>
            <tbody>
              {records.slice(0, TABLE_PREVIEW_LIMIT).map((record, index) => (
                <tr key={`${record.event_id}-${record.track_id}-${index}`}>
                  <td className="cell-id" title={formatValue(record.event_id)}>
                    {formatValue(record.event_id)}
                  </td>
                  <td className="cell-id" title={formatValue(record.track_id)}>
                    {formatValue(record.track_id)}
                  </td>
                  <td className="cell-id" title={formatValue(record.zone_id)}>
                    {formatValue(record.zone_id)}
                  </td>
                  <td className="cell-id" title={formatValue(record.counting_line_id)}>
                    {formatValue(record.counting_line_id)}
                  </td>
                  <td>{formatValue(record.class_name)}</td>
                  <td>{formatValue(record.direction)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <PreviewNotice total={records.length} limit={TABLE_PREVIEW_LIMIT} />
        </>
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
        {formatValue(data.summary?.zone_count ?? 0)} 区域 ·{" "}
        {formatValue(data.summary?.total_windows ?? 0)} 窗口 ·{" "}
        {formatValue(data.summary?.congestion_event_count ?? 0)} 拥堵事件 ·{" "}
        {windows.length} 窗口行 · {congestionEvents.length} 事件行
      </p>
      <p className="muted">
        schema {formatValue(data.schema_version)} · window {formatValue(data.window_ms)} ms
      </p>
      <h3>区域窗口</h3>
      {windows.length === 0 ? (
        <p className="muted">暂无 zone windows</p>
      ) : (
        <>
          <table>
            <caption className="sr-only">区域窗口</caption>
            <thead>
              <tr>
                <th scope="col">窗口</th>
                <th scope="col">区域</th>
                <th scope="col">车辆</th>
                <th scope="col">行人</th>
                <th scope="col">占用</th>
                <th scope="col">平均速度</th>
              </tr>
            </thead>
            <tbody>
              {windows.slice(0, TABLE_PREVIEW_LIMIT).map((window, index) => (
                <tr key={`${window.time_window_start_ms}-${window.zone_id}-${index}`}>
                  <td>
                    {formatValue(window.time_window_start_ms)} -{" "}
                    {formatValue(window.time_window_end_ms)}
                  </td>
                  <td className="cell-id" title={formatValue(window.zone_id)}>
                    {formatValue(window.zone_id)}
                  </td>
                  <td>{formatValue(window.vehicle_count)}</td>
                  <td>{formatValue(window.person_count)}</td>
                  <td>{formatValue(window.occupancy_count)}</td>
                  <td>{formatValue(window.avg_speed_px_per_frame)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <PreviewNotice total={windows.length} limit={TABLE_PREVIEW_LIMIT} />
        </>
      )}
      <h3>拥堵事件</h3>
      {congestionEvents.length === 0 ? (
        <p className="muted">暂无 congestion events</p>
      ) : (
        <>
          <table>
            <caption className="sr-only">拥堵事件</caption>
            <thead>
              <tr>
                <th scope="col">事件</th>
                <th scope="col">区域</th>
                <th scope="col">帧</th>
                <th scope="col">时间戳</th>
                <th scope="col">车辆</th>
                <th scope="col">平均速度</th>
              </tr>
            </thead>
            <tbody>
              {congestionEvents.slice(0, TABLE_PREVIEW_LIMIT).map((event, index) => (
                <tr key={`${event.event_id}-${index}`}>
                  <td className="cell-id" title={formatValue(event.event_id)}>
                    {formatValue(event.event_id)}
                  </td>
                  <td className="cell-id" title={formatValue(event.zone_id)}>
                    {formatValue(event.zone_id)}
                  </td>
                  <td>{formatValue(event.frame_index)}</td>
                  <td>{formatValue(event.timestamp_ms)}</td>
                  <td>{formatValue(event.vehicle_count)}</td>
                  <td>{formatValue(event.avg_speed_px_per_frame)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <PreviewNotice total={congestionEvents.length} limit={TABLE_PREVIEW_LIMIT} />
        </>
      )}
    </>
  );
}

function RecordTable({
  caption,
  columns,
  rows
}: {
  caption: string;
  columns: readonly string[];
  rows: Array<AlertRecord | EventRecord | EventEvidenceRecord | RuleExecutionRecord>;
}) {
  return (
    <table>
      <caption className="sr-only">{caption}</caption>
      <thead>
        <tr>
          {columns.map((column) => (
            <th key={column} scope="col">{column}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, index) => (
          <tr
            key={`${formatValue(row.alert_id)}-${formatValue(row.event_id)}-${formatValue(row.rule_id)}-${index}`}
          >
            {columns.map((column) => (
              <td
                className={tableCellClassName(column)}
                key={column}
                title={tableCellTitle(column, row[column])}
              >
                {formatValue(row[column])}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function tableCellClassName(column: string): string | undefined {
  const normalized = column.toLowerCase();
  if (normalized.includes("path") || normalized.includes("dir")) {
    return "cell-path";
  }
  if (normalized.endsWith("id") || normalized.includes("_id")) {
    return "cell-id";
  }
  return undefined;
}

function tableCellTitle(column: string, value: unknown): string | undefined {
  if (!tableCellClassName(column)) {
    return undefined;
  }
  const displayValue = formatValue(value);
  return displayValue === "-" ? undefined : displayValue;
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

function topCountLabel(value: Record<string, number> | undefined): string {
  const [key, count] = Object.entries(value ?? {}).sort((left, right) => right[1] - left[1])[0] ?? [];
  return key ? `${key}:${count}` : "-";
}

function countRowsByStatus(rows: RuleExecutionRecord[], status: string): number {
  return rows.filter((row) => String(row.status ?? "").toLowerCase() === status).length;
}

function artifactStatus(summary: ArtifactSummary | undefined, key: string): string {
  return summary?.[key]?.status ?? "-";
}

function artifactRecordCount(summary: ArtifactSummary | undefined, key: string): string {
  const item = summary?.[key];
  if (!item) {
    return "-";
  }
  return item.record_count !== undefined ? String(item.record_count) : item.status;
}

function artifactSummaryLabel(summary: ArtifactSummary | undefined): string {
  const items = Object.values(summary ?? {});
  if (items.length === 0) {
    return "-";
  }
  const availableCount = items.filter((item) => item.status === "available").length;
  return `${availableCount}/${items.length} 可用`;
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
