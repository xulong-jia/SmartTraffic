import { useEffect, useMemo, useState } from "react";

import {
  createCamera,
  disableCamera,
  enableCamera,
  listCameras
} from "../api/cameras";
import {
  getRecentAlerts,
  getRecentEvents,
  getRecentFrames,
  getRealtimeStatus,
  startRealtimePreview,
  stopRealtimePreview
} from "../api/realtime";
import type {
  CameraCreatePayload,
  CameraRecord,
  CameraSourceType,
  RealtimeAlert,
  RealtimeEvent,
  RealtimeFrame,
  RealtimeStatus
} from "../types";
import {
  buildAlertRows,
  buildEventRows,
  buildFrameRows,
  buildMaskedStreamDisplay,
  buildRealtimeStatusCards,
  buildStartDisabledReason,
  formatCameraSourceLabel
} from "../utils/realtimePreview";

const initialForm: CameraCreatePayload = {
  name: "Mock Intersection Camera",
  location: "demo-intersection",
  source_type: "mock",
  stream_url: "",
  enabled: true,
  width: 1280,
  height: 720,
  fps: 10
};

export default function CameraCenterPage() {
  const [cameras, setCameras] = useState<CameraRecord[]>([]);
  const [selectedCameraId, setSelectedCameraId] = useState("");
  const [form, setForm] = useState<CameraCreatePayload>(initialForm);
  const [status, setStatus] = useState<RealtimeStatus | null>(null);
  const [frames, setFrames] = useState<RealtimeFrame[]>([]);
  const [events, setEvents] = useState<RealtimeEvent[]>([]);
  const [alerts, setAlerts] = useState<RealtimeAlert[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const selectedCamera = useMemo(
    () => cameras.find((camera) => camera.id === selectedCameraId) || null,
    [cameras, selectedCameraId]
  );
  const statusCards = buildRealtimeStatusCards(status);
  const frameRows = buildFrameRows(frames);
  const eventRows = buildEventRows(events);
  const alertRows = buildAlertRows(alerts);
  const startDisabledReason = buildStartDisabledReason(selectedCamera);

  useEffect(() => {
    void refreshCameras();
  }, []);

  async function refreshCameras(nextSelectedId = selectedCameraId) {
    setLoading(true);
    setError("");
    try {
      const payload = await listCameras();
      setCameras(payload);
      const nextId = nextSelectedId || payload[0]?.id || "";
      setSelectedCameraId(nextId);
      if (nextId) {
        await refreshRealtime(nextId);
      } else {
        resetRealtime();
      }
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Camera request failed");
    } finally {
      setLoading(false);
    }
  }

  async function submitCamera() {
    setLoading(true);
    setError("");
    setSuccessMessage("");
    try {
      const created = await createCamera({
        ...form,
        stream_url: form.stream_url?.trim() || null,
        location: form.location?.trim() || null
      });
      setSuccessMessage(`Created ${created.name}.`);
      await refreshCameras(created.id);
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Create camera failed");
    } finally {
      setLoading(false);
    }
  }

  async function setSelectedCamera(cameraId: string) {
    setSelectedCameraId(cameraId);
    if (cameraId) {
      await refreshRealtime(cameraId);
    } else {
      resetRealtime();
    }
  }

  async function refreshRealtime(cameraId = selectedCameraId) {
    if (!cameraId) {
      resetRealtime();
      return;
    }
    const [nextStatus, nextFrames, nextEvents, nextAlerts] = await Promise.all([
      getRealtimeStatus(cameraId),
      getRecentFrames(cameraId),
      getRecentEvents(cameraId),
      getRecentAlerts(cameraId)
    ]);
    setStatus(nextStatus);
    setFrames(nextFrames.items);
    setEvents(nextEvents.items);
    setAlerts(nextAlerts.items);
  }

  async function startSelectedCamera() {
    if (!selectedCamera) {
      return;
    }
    setLoading(true);
    setError("");
    setSuccessMessage("");
    try {
      const nextStatus = await startRealtimePreview(selectedCamera.id);
      setStatus(nextStatus);
      await refreshRealtime(selectedCamera.id);
      setSuccessMessage(`Started ${selectedCamera.name}.`);
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Start preview failed");
    } finally {
      setLoading(false);
    }
  }

  async function stopSelectedCamera() {
    if (!selectedCamera) {
      return;
    }
    setLoading(true);
    setError("");
    setSuccessMessage("");
    try {
      const nextStatus = await stopRealtimePreview(selectedCamera.id);
      setStatus(nextStatus);
      await refreshRealtime(selectedCamera.id);
      setSuccessMessage(`Stopped ${selectedCamera.name}.`);
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Stop preview failed");
    } finally {
      setLoading(false);
    }
  }

  async function toggleSelectedCamera() {
    if (!selectedCamera) {
      return;
    }
    setLoading(true);
    setError("");
    setSuccessMessage("");
    try {
      const updated = selectedCamera.enabled
        ? await disableCamera(selectedCamera.id)
        : await enableCamera(selectedCamera.id);
      setSuccessMessage(`${updated.name} ${updated.enabled ? "enabled" : "disabled"}.`);
      await refreshCameras(updated.id);
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Camera update failed");
    } finally {
      setLoading(false);
    }
  }

  function resetRealtime() {
    setStatus(null);
    setFrames([]);
    setEvents([]);
    setAlerts([]);
  }

  return (
    <>
      <header className="page-header">
        <div>
          <h2>Camera Center</h2>
          <p>DB-backed cameras and realtime preview metadata.</p>
        </div>
        <button type="button" onClick={() => refreshCameras()} disabled={loading}>
          Refresh
        </button>
      </header>

      {error ? <p className="status-pill status-error">{error}</p> : null}
      {successMessage ? <p className="status-pill status-completed">{successMessage}</p> : null}

      <section className="grid two">
        <div className="panel">
          <h3>Create Camera</h3>
          <div className="toolbar">
            <label>
              Name
              <input
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
              />
            </label>
            <label>
              Source
              <select
                value={form.source_type}
                onChange={(event) =>
                  setForm({ ...form, source_type: event.target.value as CameraSourceType })
                }
              >
                <option value="mock">Mock</option>
                <option value="file">Local file</option>
                <option value="rtsp">RTSP</option>
                <option value="upload">Upload</option>
              </select>
            </label>
            <label>
              Location
              <input
                value={form.location || ""}
                onChange={(event) => setForm({ ...form, location: event.target.value })}
              />
            </label>
            <label>
              URL / path
              <input
                value={form.stream_url || ""}
                onChange={(event) => setForm({ ...form, stream_url: event.target.value })}
              />
            </label>
            <label>
              Width
              <input
                min="0"
                type="number"
                value={form.width || 0}
                onChange={(event) => setForm({ ...form, width: Number(event.target.value) })}
              />
            </label>
            <label>
              Height
              <input
                min="0"
                type="number"
                value={form.height || 0}
                onChange={(event) => setForm({ ...form, height: Number(event.target.value) })}
              />
            </label>
            <label>
              FPS
              <input
                min="0"
                step="0.1"
                type="number"
                value={form.fps || 0}
                onChange={(event) => setForm({ ...form, fps: Number(event.target.value) })}
              />
            </label>
          </div>
          <button type="button" onClick={submitCamera} disabled={loading || !form.name.trim()}>
            Create
          </button>
        </div>

        <div className="panel">
          <h3>Realtime Preview</h3>
          <div className="toolbar">
            <label>
              Camera
              <select
                value={selectedCameraId}
                onChange={(event) => void setSelectedCamera(event.target.value)}
              >
                <option value="">Select camera</option>
                {cameras.map((camera) => (
                  <option key={camera.id} value={camera.id}>
                    {camera.name}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              onClick={startSelectedCamera}
              disabled={loading || Boolean(startDisabledReason)}
              title={startDisabledReason || "Start preview"}
            >
              Start
            </button>
            <button type="button" onClick={stopSelectedCamera} disabled={loading || !selectedCamera}>
              Stop
            </button>
            <button type="button" onClick={toggleSelectedCamera} disabled={loading || !selectedCamera}>
              {selectedCamera?.enabled ? "Disable" : "Enable"}
            </button>
          </div>

          {selectedCamera ? (
            <dl className="detail-grid">
              <div>
                <dt>Source</dt>
                <dd>{formatCameraSourceLabel(selectedCamera.source_type)}</dd>
              </div>
              <div>
                <dt>Masked stream</dt>
                <dd>{buildMaskedStreamDisplay(selectedCamera)}</dd>
              </div>
              <div>
                <dt>Enabled</dt>
                <dd>{selectedCamera.enabled ? "Yes" : "No"}</dd>
              </div>
            </dl>
          ) : null}

          <div className="metric-row">
            {statusCards.map((card) => (
              <div className="metric-card" key={card.label}>
                <span className="muted">{card.label}</span>
                <span className="metric-value">{card.value}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="panel">
        <h3>Recent Frames</h3>
        <table>
          <thead>
            <tr>
              <th>Frame</th>
              <th>Source</th>
              <th>Status</th>
              <th>Timestamp</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            {frameRows.map((frame) => (
              <tr key={frame.id}>
                <td>{frame.frame}</td>
                <td>{frame.source}</td>
                <td>{frame.status}</td>
                <td>{frame.timestamp}</td>
                <td>{frame.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="grid two">
        <div className="panel">
          <h3>Recent Events</h3>
          <table>
            <thead>
              <tr>
                <th>Type</th>
                <th>Severity</th>
                <th>Frame</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {eventRows.map((event) => (
                <tr key={event.id}>
                  <td>{event.type}</td>
                  <td>{event.severity}</td>
                  <td>{event.frame}</td>
                  <td>{event.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="panel">
          <h3>Recent Alerts</h3>
          <table>
            <thead>
              <tr>
                <th>Level</th>
                <th>Type</th>
                <th>Status</th>
                <th>Message</th>
              </tr>
            </thead>
            <tbody>
              {alertRows.map((alert) => (
                <tr key={alert.id}>
                  <td>{alert.level}</td>
                  <td>{alert.type}</td>
                  <td>{alert.status}</td>
                  <td>{alert.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
