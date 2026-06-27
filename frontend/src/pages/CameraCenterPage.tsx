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
  name: "Mock 路口摄像头",
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
      setSuccessMessage(`已创建 Created ${created.name}.`);
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
      setSuccessMessage(`已启动 Started ${selectedCamera.name}.`);
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
      setSuccessMessage(`已停止 Stopped ${selectedCamera.name}.`);
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
      setSuccessMessage(`${updated.name} ${updated.enabled ? "已启用 enabled" : "已停用 disabled"}.`);
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
          <h2>摄像头中心 Camera Center</h2>
          <p>管理本地摄像头、文件源和 RTSP 预览配置。</p>
        </div>
        <button type="button" onClick={() => refreshCameras()} disabled={loading}>
          刷新 Refresh
        </button>
      </header>

      {error ? <p className="status-pill status-error">{error}</p> : null}
      {successMessage ? <p className="status-pill status-completed">{successMessage}</p> : null}

      <section className="grid two content-grid">
        <div className="panel">
          <h3>创建摄像头 Create Camera</h3>
          <div className="form-grid">
            <label>
              名称 Name
              <input
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
              />
            </label>
            <label>
              来源 Source
              <select
                value={form.source_type}
                onChange={(event) =>
                  setForm({ ...form, source_type: event.target.value as CameraSourceType })
                }
              >
                <option value="mock">模拟 Mock</option>
                <option value="file">本地文件 Local file</option>
                <option value="rtsp">RTSP</option>
                <option value="upload">上传 Upload</option>
              </select>
            </label>
            <label>
              位置 Location
              <input
                value={form.location || ""}
                onChange={(event) => setForm({ ...form, location: event.target.value })}
              />
            </label>
            <label>
              URL / 路径 URL / path
              <input
                value={form.stream_url || ""}
                onChange={(event) => setForm({ ...form, stream_url: event.target.value })}
              />
            </label>
            <label>
              宽度 Width
              <input
                min="0"
                type="number"
                value={form.width || 0}
                onChange={(event) => setForm({ ...form, width: Number(event.target.value) })}
              />
            </label>
            <label>
              高度 Height
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
            创建 Create
          </button>
        </div>

        <div className="panel">
          <h3>实时预览 Realtime Preview</h3>
          <div className="toolbar">
            <label>
              摄像头 Camera
              <select
                value={selectedCameraId}
                onChange={(event) => void setSelectedCamera(event.target.value)}
              >
                <option value="">选择摄像头 Select camera</option>
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
              启动 Start
            </button>
            <button type="button" onClick={stopSelectedCamera} disabled={loading || !selectedCamera}>
              停止 Stop
            </button>
            <button type="button" onClick={toggleSelectedCamera} disabled={loading || !selectedCamera}>
              {selectedCamera?.enabled ? "停用 Disable" : "启用 Enable"}
            </button>
          </div>

          {selectedCamera ? (
            <dl className="detail-grid">
              <div>
                <dt>来源 Source</dt>
                <dd>{formatCameraSourceLabel(selectedCamera.source_type)}</dd>
              </div>
              <div>
                <dt>脱敏流地址 Masked stream</dt>
                <dd>{buildMaskedStreamDisplay(selectedCamera)}</dd>
              </div>
              <div>
                <dt>启用状态 Enabled</dt>
                <dd>{selectedCamera.enabled ? "是 Yes" : "否 No"}</dd>
              </div>
            </dl>
          ) : null}

          <div className="metric-row">
            {statusCards.map((card) => (
              <RealtimeMetricCard key={card.label} label={card.label} value={card.value} />
            ))}
          </div>
        </div>
      </section>

      <section className="panel">
        <h3>最近帧 Recent Frames</h3>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>帧 Frame</th>
                <th>来源 Source</th>
                <th>状态 Status</th>
                <th>时间戳 Timestamp</th>
                <th>说明 Description</th>
              </tr>
            </thead>
            <tbody>
              {frameRows.map((frame) => (
                <tr key={frame.id}>
                  <td>{frame.frame}</td>
                  <td>{frame.source}</td>
                  <td>
                    <span className={`status-pill status-${statusClassName(frame.status)}`}>
                      {frame.status}
                    </span>
                  </td>
                  <td>{frame.timestamp}</td>
                  <td className="wrap-cell">{frame.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="grid two content-grid">
        <div className="panel">
          <h3>最近事件 Recent Events</h3>
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>类型 Type</th>
                  <th>严重程度 Severity</th>
                  <th>帧 Frame</th>
                  <th>状态 Status</th>
                </tr>
              </thead>
              <tbody>
                {eventRows.map((event) => (
                  <tr key={event.id}>
                    <td>{event.type}</td>
                    <td>{event.severity}</td>
                    <td>{event.frame}</td>
                    <td>
                      <span className={`status-pill status-${statusClassName(event.status)}`}>
                        {event.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="panel">
          <h3>最近告警 Recent Alerts</h3>
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>级别 Level</th>
                  <th>类型 Type</th>
                  <th>状态 Status</th>
                  <th>消息 Message</th>
                </tr>
              </thead>
              <tbody>
                {alertRows.map((alert) => (
                  <tr key={alert.id}>
                    <td>{alert.level}</td>
                    <td>{alert.type}</td>
                    <td>
                      <span className={`status-pill status-${statusClassName(alert.status)}`}>
                        {alert.status}
                      </span>
                    </td>
                    <td className="wrap-cell">{alert.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </>
  );
}

function RealtimeMetricCard({ label, value }: { label: string; value: string | number }) {
  const status = label === "状态 Status" && typeof value === "string" ? splitStatusValue(value) : null;
  return (
    <div className="metric-card">
      <span className="metric-label">{label}</span>
      {status ? (
        <>
          <span className="metric-value metric-status-main">{status.primary}</span>
          <span className={`status-pill status-${statusClassName(status.secondary)}`}>
            {status.secondary}
          </span>
        </>
      ) : (
        <span className="metric-value">{value}</span>
      )}
    </div>
  );
}

function splitStatusValue(value: string): { primary: string; secondary: string } {
  const [primary, ...rest] = value.split(" ");
  return { primary, secondary: rest.join(" ") || value };
}

function statusClassName(value: string): string {
  const parts = value.split(" ");
  const raw = parts[parts.length - 1] || value;
  return raw.toLowerCase().replace(/[^a-z0-9_-]+/g, "_") || "unknown";
}
