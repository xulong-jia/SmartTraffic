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
  ZoneStatisticsArtifact
} from "../types";
import { getRunId } from "../utils/analysisRunMetrics";

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

const eventColumns = [
  "event_type",
  "severity",
  "status",
  "track_id",
  "class_name",
  "zone_id",
  "start_frame",
  "end_frame",
  "confidence"
] as const;

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
}

export default function AnalysisDetailPage({ initialRunId = "" }: AnalysisDetailPageProps) {
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

  return (
    <>
      <header className="page-header">
        <div>
          <h2>Analysis Detail</h2>
          <p>Run summary, artifact status, events, alerts, and Stage 6 statistics.</p>
        </div>
      </header>
      <div className="grid two">
        <div className="grid">
          <section className="panel">
            <label>
              Run ID
              <select
                value={selectedRunId}
                onChange={(event) => setSelectedRunId(event.target.value)}
              >
                <option value="">No run selected</option>
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
            {runsLoading ? <p className="muted">Loading run index...</p> : null}
            {runsError ? <p>{runsError}</p> : null}
            {runs.length === 0 && !runsLoading ? <p className="muted">No analysis runs found.</p> : null}
          </section>
          <section className="panel">
            <h3>Run Summary</h3>
            {runSummaryLoading ? <p className="muted">Loading run summary...</p> : null}
            {runSummaryError ? <p>{runSummaryError}</p> : null}
            {runSummary ? <RunSummaryPanel run={runSummary} /> : null}
          </section>
          <section className="panel">
            <h3>Index Status</h3>
            {manifestLoading ? <p className="muted">Loading manifest endpoint...</p> : null}
            {manifestError ? <p>{manifestError}</p> : null}
            {runSummary ? (
              <IndexStatusPanel manifestPayload={manifestPayload} run={runSummary} />
            ) : (
              <p className="muted">Select a run to inspect metadata, manifest, and artifact index.</p>
            )}
          </section>
          <section className="panel">
            <h3>Artifact Summary</h3>
            <ArtifactSummaryTable artifactSummary={runSummary?.artifact_summary} />
          </section>
          <section className="panel">
            <h3>Visual Artifacts</h3>
            <VisualArtifactsPanel artifactSummary={runSummary?.artifact_summary} />
          </section>
        </div>
        <div className="grid">
          <section className="panel">
            <h3>Trajectory Query</h3>
            <div className="toolbar">
              <label>
                Limit
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
                Apply / Refresh
              </button>
            </div>
            {trajectoryLoading ? <p className="muted">Loading trajectory points...</p> : null}
            {trajectoryError ? <p>{trajectoryError}</p> : null}
            {trajectoryData ? <TrajectoryDetail data={trajectoryData} /> : null}
          </section>
          <section className="panel">
            <h3>Event Query</h3>
            <div className="toolbar">
              <label>
                Limit
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
                Event type
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
                Apply / Refresh
              </button>
            </div>
            {eventsLoading ? <p className="muted">Loading events...</p> : null}
            {eventsError ? <p>{eventsError}</p> : null}
            {eventsData ? <EventsDetail data={eventsData} /> : null}
          </section>
          <section className="panel">
            <h3>Alert Query</h3>
            <div className="toolbar">
              <label>
                Limit
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
                Status
                <input
                  placeholder="all"
                  value={alertStatusFilter}
                  onChange={(event) => setAlertStatusFilter(event.target.value)}
                />
              </label>
              <label>
                Level
                <input
                  placeholder="all"
                  value={alertLevelFilter}
                  onChange={(event) => setAlertLevelFilter(event.target.value)}
                />
              </label>
              <label>
                Event type
                <input
                  placeholder="all"
                  value={alertEventTypeFilter}
                  onChange={(event) => setAlertEventTypeFilter(event.target.value)}
                />
              </label>
              <button disabled={!selectedRunId || alertsLoading} type="button" onClick={handleGenerateAlerts}>
                Generate alerts from events
              </button>
              <button disabled={!selectedRunId || alertsLoading} type="button" onClick={handleAlertsRefresh}>
                Refresh alerts
              </button>
            </div>
            {alertsLoading ? <p className="muted">Loading alerts...</p> : null}
            {alertsError ? <p>{alertsError}</p> : null}
            {alertsData ? <AlertsDetail data={alertsData} /> : null}
          </section>
          <section className="panel">
            <div className="section-heading-row">
              <h3>Flow Counts</h3>
              <button
                disabled={!selectedRunId || flowCountsLoading}
                type="button"
                onClick={() => selectedRunId && loadFlowCounts(selectedRunId)}
              >
                Refresh
              </button>
            </div>
            {flowCountsLoading ? <p className="muted">Loading flow_counts.json...</p> : null}
            {flowCountsError ? <p>{flowCountsError}</p> : null}
            {flowCountsData ? <FlowCountsDetail data={flowCountsData} /> : null}
          </section>
          <section className="panel">
            <div className="section-heading-row">
              <h3>Zone Statistics</h3>
              <button
                disabled={!selectedRunId || zoneStatisticsLoading}
                type="button"
                onClick={() => selectedRunId && loadZoneStatistics(selectedRunId)}
              >
                Refresh
              </button>
            </div>
            {zoneStatisticsLoading ? <p className="muted">Loading zone_statistics.json...</p> : null}
            {zoneStatisticsError ? <p>{zoneStatisticsError}</p> : null}
            {zoneStatisticsData ? <ZoneStatisticsDetail data={zoneStatisticsData} /> : null}
          </section>
          <section className="panel">
            <h3>Detection Summary</h3>
            {detectionsLoading ? <p className="muted">Loading detections...</p> : null}
            {detectionsError ? <p>{detectionsError}</p> : null}
            {detections ? (
              <>
              <p>
                {detections.summary.total_frames_processed} frames ·{" "}
                {detections.summary.total_detections} detections
              </p>
              <h3>Frame Results</h3>
              <table>
                <thead>
                  <tr>
                    <th>Frame</th>
                    <th>Timestamp</th>
                    <th>Detections</th>
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
            <h3>Tracking Summary</h3>
            {tracksLoading ? <p className="muted">Loading tracks...</p> : null}
            {tracksError ? <p>{tracksError}</p> : null}
            {tracks ? (
              <>
              <p>
                {tracks.summary.total_frames_processed} frames · {tracks.summary.total_tracks} track rows ·{" "}
                {tracks.summary.unique_track_ids} unique IDs
              </p>
              <h3>Track Results</h3>
              <table>
                <thead>
                  <tr>
                    <th>Frame</th>
                    <th>Track ID</th>
                    <th>Class</th>
                    <th>State</th>
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
        <dt>status</dt>
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
            <th>Status</th>
            <th>Available</th>
            <th>Path</th>
            <th>Schema</th>
            <th>Error</th>
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
    return <p className="muted">No artifact summary available.</p>;
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Artifact key</th>
          <th>Status</th>
          <th>Path</th>
          <th>Record count</th>
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
    return <p className="muted">No visual artifact status available.</p>;
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Artifact</th>
          <th>Status</th>
          <th>Count</th>
          <th>Path</th>
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
      <h3>Trajectory Summary</h3>
      <p>
        {formatValue(data.summary.total_frames_processed ?? 0)} frames ·{" "}
        {formatValue(data.summary.total_trajectory_points ?? 0)} trajectory points ·{" "}
        {formatValue(data.summary.unique_track_ids ?? 0)} unique IDs · avg length{" "}
        {formatValue(data.summary.avg_track_length)} · max length{" "}
        {formatValue(data.summary.max_track_length)} · avg speed{" "}
        {formatValue(data.summary.avg_speed_px_per_second)}
      </p>
      {hasNoMatches ? <p className="muted">没有匹配的 trajectory points</p> : null}
      <h3>Trajectory Rows</h3>
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
      <h3>Trajectory Frames</h3>
      {framePreview.length === 0 ? (
        <p className="muted">暂无 trajectory frames</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Frame</th>
              <th>Timestamp</th>
              <th>Point count</th>
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

function EventsDetail({ data }: { data: EventsResponse }) {
  const eventPreview = data.events.slice(0, 20);
  const evidencePreview = data.event_evidence.slice(0, 20);
  const executionPreview = data.rule_executions.slice(0, 20);

  return (
    <>
      <h3>Event Summary</h3>
      <p>
        {formatValue(data.summary.total_events ?? 0)} events ·{" "}
        {formatValue(data.summary.unique_track_ids ?? 0)} unique IDs · first{" "}
        {formatValue(data.summary.first_event_time_ms)} · last{" "}
        {formatValue(data.summary.last_event_time_ms)}
      </p>
      <p className="muted">
        types {formatCountMap(data.summary.per_event_type_counts)} · severity{" "}
        {formatCountMap(data.summary.per_severity_counts)} · status{" "}
        {formatCountMap(data.summary.per_status_counts)}
      </p>
      <h3>Events</h3>
      {eventPreview.length === 0 ? (
        <p className="muted">暂无 events</p>
      ) : (
        <RecordTable columns={eventColumns} rows={eventPreview} />
      )}
      <h3>Event Evidence</h3>
      {evidencePreview.length === 0 ? (
        <p className="muted">暂无 event evidence</p>
      ) : (
        <RecordTable columns={evidenceColumns} rows={evidencePreview} />
      )}
      <h3>Rule Executions</h3>
      {executionPreview.length === 0 ? (
        <p className="muted">暂无 rule executions</p>
      ) : (
        <RecordTable columns={ruleExecutionColumns} rows={executionPreview} />
      )}
    </>
  );
}

function AlertsDetail({ data }: { data: AlertsResponse }) {
  const alertPreview = data.alerts.slice(0, 20);

  return (
    <>
      <h3>Alert Summary</h3>
      <p>
        {formatValue(data.summary.total_alerts ?? 0)} alerts ·{" "}
        {formatValue(data.summary.unique_event_ids ?? 0)} events ·{" "}
        {formatValue(data.summary.unique_track_ids ?? 0)} unique IDs · first{" "}
        {formatValue(data.summary.first_alert_time_ms)} · last{" "}
        {formatValue(data.summary.last_alert_time_ms)}
      </p>
      <p className="muted">
        types {formatCountMap(data.summary.per_alert_type_counts)} · level{" "}
        {formatCountMap(data.summary.per_level_counts)} · status{" "}
        {formatCountMap(data.summary.per_status_counts)}
      </p>
      <h3>Alerts</h3>
      {alertPreview.length === 0 ? (
        <p className="muted">暂无 alerts</p>
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
        {formatValue(data.summary?.total_count ?? 0)} total ·{" "}
        {formatValue(data.summary?.vehicle_count ?? 0)} vehicles ·{" "}
        {formatValue(data.summary?.person_count ?? 0)} people · {records.length} records ·{" "}
        {windows.length} windows
      </p>
      <p className="muted">
        schema {formatValue(data.schema_version)} · window {formatValue(data.window_ms)} ms
      </p>
      <h3>Flow Windows</h3>
      {windows.length === 0 ? (
        <p className="muted">暂无 flow windows</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Window</th>
              <th>Zone</th>
              <th>Line</th>
              <th>Class</th>
              <th>Direction</th>
              <th>Total</th>
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
      <h3>Flow Records</h3>
      {records.length === 0 ? (
        <p className="muted">暂无 flow records</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Event</th>
              <th>Track</th>
              <th>Zone</th>
              <th>Line</th>
              <th>Class</th>
              <th>Direction</th>
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
        {formatValue(data.summary?.zone_count ?? 0)} zones ·{" "}
        {formatValue(data.summary?.total_windows ?? 0)} windows ·{" "}
        {formatValue(data.summary?.congestion_event_count ?? 0)} congestion events ·{" "}
        {windows.length} window rows · {congestionEvents.length} event rows
      </p>
      <p className="muted">
        schema {formatValue(data.schema_version)} · window {formatValue(data.window_ms)} ms
      </p>
      <h3>Zone Windows</h3>
      {windows.length === 0 ? (
        <p className="muted">暂无 zone windows</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Window</th>
              <th>Zone</th>
              <th>Vehicles</th>
              <th>People</th>
              <th>Occupancy</th>
              <th>Avg speed</th>
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
      <h3>Congestion Events</h3>
      {congestionEvents.length === 0 ? (
        <p className="muted">暂无 congestion events</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Event</th>
              <th>Zone</th>
              <th>Frame</th>
              <th>Timestamp</th>
              <th>Vehicles</th>
              <th>Avg speed</th>
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

function clampInteger(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) {
    return min;
  }
  return Math.min(max, Math.max(min, Math.trunc(value)));
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  if (typeof value === "number" && !Number.isFinite(value)) {
    return "-";
  }
  if (Array.isArray(value) || typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
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
