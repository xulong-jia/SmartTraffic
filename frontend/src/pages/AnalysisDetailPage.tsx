import { useEffect, useState } from "react";

import {
  generateAlerts,
  getAnalysisRunDetections,
  getAnalysisRunTracks,
  getAlerts,
  getEvents,
  getTrajectoryPoints,
  listAnalysisRuns
} from "../api/analysisRuns";
import VideoPlayerWithOverlay from "../components/VideoPlayerWithOverlay";
import type {
  AlertRecord,
  AlertsResponse,
  AnalysisRun,
  AnalysisRunDetections,
  AnalysisRunTracks,
  EventEvidenceRecord,
  EventRecord,
  EventsResponse,
  RuleExecutionRecord,
  TrajectoryFrame,
  TrajectoryPointRow,
  TrajectoryPointsResponse
} from "../types";

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

export default function AnalysisDetailPage() {
  const [runs, setRuns] = useState<AnalysisRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState("");
  const [detections, setDetections] = useState<AnalysisRunDetections | null>(null);
  const [tracks, setTracks] = useState<AnalysisRunTracks | null>(null);
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
  const [error, setError] = useState("");

  useEffect(() => {
    listAnalysisRuns()
      .then((items) => {
        setRuns(items);
        if (items.length > 0) {
          setSelectedRunId(items[items.length - 1].id);
        }
      })
      .catch((currentError: Error) => setError(currentError.message));
  }, []);

  useEffect(() => {
    if (!selectedRunId) {
      return;
    }
    setError("");
    Promise.all([
      getAnalysisRunDetections(selectedRunId, 50),
      getAnalysisRunTracks(selectedRunId, 50)
    ])
      .then(([detectionPayload, trackingPayload]) => {
        setDetections(detectionPayload);
        setTracks(trackingPayload);
      })
      .catch((currentError: Error) => setError(currentError.message));
    loadTrajectory(selectedRunId);
    loadEvents(selectedRunId);
    loadAlerts(selectedRunId);
  }, [selectedRunId]);

  async function loadTrajectory(runId: string) {
    setTrajectoryLoading(true);
    setTrajectoryError("");
    setTrajectoryData(null);
    try {
      const payload = await getTrajectoryPoints(runId, {
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
      const payload = await getEvents(runId, {
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
      const payload = await getAlerts(runId, {
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
          <p>阶段三检测与跟踪结果</p>
        </div>
      </header>
      <div className="grid two">
        <VideoPlayerWithOverlay title="Tracking preview placeholder" />
        <div className="grid">
          <section className="panel">
            <label>
              Run ID
              <select value={selectedRunId} onChange={(event) => setSelectedRunId(event.target.value)}>
                <option value="">No run selected</option>
                {runs.map((run) => (
                  <option key={run.id} value={run.id}>
                    {run.id}
                  </option>
                ))}
              </select>
            </label>
            {error ? <p>{error}</p> : null}
          </section>
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
          {detections ? (
            <section className="panel">
              <h3>Detection Summary</h3>
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
            </section>
          ) : null}
          {tracks ? (
            <section className="panel">
              <h3>Tracking Summary</h3>
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
            </section>
          ) : null}
        </div>
      </div>
    </>
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
