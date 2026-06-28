import { useEffect, useState, type MouseEvent } from "react";
import {
  createEventRule,
  deleteEventRule,
  listEventRules,
  updateEventRule
} from "../api/eventRules";
import { createZone, deleteZone, listZones, updateZone } from "../api/zones";
import type { EventRuleRecord, ZoneRecord } from "../types";
import {
  clampPoint,
  lineAngleDegrees,
  type EditorLine,
  type EditorPoint
} from "../utils/zoneEditorGeometry";
import {
  addPointForMode,
  buildZonePatchPayload,
  buildZonePayload,
  clearDrawingForMode,
  createEmptyZoneEditorState,
  DRAWING_MODES,
  type DrawingMode,
  validateZoneEditorState,
  zoneToEditorState,
  ZONE_TYPES,
  type ZoneEditorState
} from "../utils/zoneEditorState";
import {
  buildEventRulePatchPayload,
  buildEventRulePayload,
  createEmptyEventRuleFormState,
  eventRuleToFormState,
  EVENT_RULE_SEVERITIES,
  EVENT_TYPES,
  type EventRuleFormState
} from "../utils/zoneRuleConfigApi";

const EDITOR_WIDTH = 960;
const EDITOR_HEIGHT = 540;

export default function ZoneEditor() {
  const [zones, setZones] = useState<ZoneRecord[]>([]);
  const [rules, setRules] = useState<EventRuleRecord[]>([]);
  const [zoneState, setZoneState] = useState<ZoneEditorState>(createEmptyZoneEditorState());
  const [ruleState, setRuleState] = useState<EventRuleFormState>(createEmptyEventRuleFormState());
  const [mode, setMode] = useState<DrawingMode>("polygon");
  const [loading, setLoading] = useState(true);
  const [savingZone, setSavingZone] = useState(false);
  const [savingRule, setSavingRule] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    void loadConfig();
  }, []);

  async function loadConfig() {
    setLoading(true);
    setError(null);
    try {
      const [zoneRows, ruleRows] = await Promise.all([listZones(), listEventRules()]);
      setZones(zoneRows);
      setRules(ruleRows);
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Failed to load config.");
    } finally {
      setLoading(false);
    }
  }

  function handleEditorClick(event: MouseEvent<SVGSVGElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    const point: EditorPoint = clampPoint({
      x: ((event.clientX - rect.left) / rect.width) * EDITOR_WIDTH,
      y: ((event.clientY - rect.top) / rect.height) * EDITOR_HEIGHT
    }, EDITOR_WIDTH, EDITOR_HEIGHT);
    setZoneState((current) => addPointForMode(current, mode, point));
    setMessage(null);
    setError(null);
  }

  async function handleSaveZone() {
    const validation = validateZoneEditorState(zoneState, mode);
    if (!validation.valid) {
      setError(validation.errors.join(" "));
      return;
    }
    setSavingZone(true);
    setError(null);
    setMessage(null);
    try {
      const saved = zoneState.id
        ? await updateZone(zoneState.id, buildZonePatchPayload(zoneState))
        : await createZone(buildZonePayload(zoneState));
      await loadConfig();
      setZoneState((current) => ({ ...current, id: saved.id, version: saved.version }));
      setMessage(`区域已保存：${saved.name}。`);
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Failed to save zone.");
    } finally {
      setSavingZone(false);
    }
  }

  async function handleDeleteZone() {
    if (!zoneState.id) {
      return;
    }
    setSavingZone(true);
    setError(null);
    setMessage(null);
    try {
      await deleteZone(zoneState.id);
      await loadConfig();
      setZoneState(createEmptyZoneEditorState());
      setMessage("区域已删除。");
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Failed to delete zone.");
    } finally {
      setSavingZone(false);
    }
  }

  async function handleSaveRule() {
    setSavingRule(true);
    setError(null);
    setMessage(null);
    try {
      const saved = ruleState.id
        ? await saveExistingRule(ruleState)
        : await saveNewRule(ruleState);
      await loadConfig();
      setRuleState(eventRuleToFormState(saved));
      setMessage(`事件规则已保存：${saved.name}。`);
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Failed to save rule.");
    } finally {
      setSavingRule(false);
    }
  }

  async function saveExistingRule(state: EventRuleFormState): Promise<EventRuleRecord> {
    if (!state.id) {
      throw new Error("Rule id is required.");
    }
    const result = buildEventRulePatchPayload(state);
    if (!result.payload) {
      throw new Error(result.errors.join(" "));
    }
    return updateEventRule(state.id, result.payload);
  }

  async function saveNewRule(state: EventRuleFormState): Promise<EventRuleRecord> {
    const result = buildEventRulePayload(state);
    if (!result.payload) {
      throw new Error(result.errors.join(" "));
    }
    return createEventRule(result.payload);
  }

  async function handleDeleteRule() {
    if (!ruleState.id) {
      return;
    }
    setSavingRule(true);
    setError(null);
    setMessage(null);
    try {
      await deleteEventRule(ruleState.id);
      await loadConfig();
      setRuleState(createEmptyEventRuleFormState());
      setMessage("事件规则已删除。");
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Failed to delete rule.");
    } finally {
      setSavingRule(false);
    }
  }

  return (
    <div className="zone-editor">
      {loading ? <div className="panel muted">正在加载区域和规则配置...</div> : null}
      {error ? <div className="alert-box error">{error}</div> : null}
      {message ? <div className="alert-box success">{message}</div> : null}

      <div className="grid zone-editor-grid">
        <section className="panel zone-editor-canvas-panel">
          <div className="section-heading-row">
            <div>
              <h3>区域画布</h3>
              <p className="muted">
                {mode === "polygon"
                  ? "多边形几何"
                  : mode === "direction"
                    ? "方向线几何"
                    : "计数线几何"}
              </p>
            </div>
            <div className="button-group">
              {DRAWING_MODES.map((drawingMode) => (
                <button
                  className={mode === drawingMode ? "active-control" : ""}
                  key={drawingMode}
                  onClick={() => setMode(drawingMode)}
                  type="button"
                >
                  {formatDrawingModeLabel(drawingMode)}
                </button>
              ))}
              <button
                onClick={() => setZoneState((current) => clearDrawingForMode(current, mode))}
                type="button"
              >
                清除
              </button>
            </div>
          </div>
          <svg
            className="zone-canvas"
            onClick={handleEditorClick}
            role="img"
            viewBox={`0 0 ${EDITOR_WIDTH} ${EDITOR_HEIGHT}`}
          >
            <rect height={EDITOR_HEIGHT} width={EDITOR_WIDTH} x="0" y="0" />
            {zoneState.polygon.length > 1 ? (
              <polyline
                className="zone-polygon-line"
                points={zoneState.polygon.map((point) => `${point.x},${point.y}`).join(" ")}
              />
            ) : null}
            {zoneState.polygon.length >= 3 ? (
              <polygon
                className="zone-polygon-fill"
                points={zoneState.polygon.map((point) => `${point.x},${point.y}`).join(" ")}
              />
            ) : null}
            {zoneState.polygon.map((point, index) => (
              <circle className="zone-point" cx={point.x} cy={point.y} key={index} r="5" />
            ))}
            <SvgEditorLine line={zoneState.directionLine} variant="direction" />
            <SvgEditorLine line={zoneState.countingLine} variant="counting" />
          </svg>
          <div className="zone-canvas-footer">
            <span>多边形点：{zoneState.polygon.length}</span>
            <span>方向角：{lineAngleDegrees(zoneState.directionLine) ?? "-"}</span>
            <span>计数线：{formatLineState(zoneState.countingLine)}</span>
          </div>
        </section>

        <section className="panel">
          <div className="section-heading-row">
            <h3>{zoneState.id ? "编辑区域" : "新建区域"}</h3>
            <button onClick={() => setZoneState(createEmptyZoneEditorState())} type="button">
              新建
            </button>
          </div>
          <div className="zone-form-grid">
            <label className="stacked-control">
              名称
              <input
                onChange={(event) =>
                  setZoneState((current) => ({ ...current, name: event.target.value }))
                }
                value={zoneState.name}
              />
            </label>
            <label className="stacked-control">
              类型
              <select
                onChange={(event) =>
                  setZoneState((current) => ({
                    ...current,
                    zoneType: event.target.value as ZoneEditorState["zoneType"]
                  }))
                }
                value={zoneState.zoneType}
              >
                {ZONE_TYPES.map((zoneType) => (
                  <option key={zoneType} value={zoneType}>
                    {formatZoneTypeLabel(zoneType)}
                  </option>
                ))}
              </select>
            </label>
            <label className="stacked-control">
              版本
              <input
                min="1"
                onChange={(event) =>
                  setZoneState((current) => ({
                    ...current,
                    version: Number(event.target.value)
                  }))
                }
                type="number"
                value={zoneState.version}
              />
            </label>
            <label className="inline-control">
              <input
                checked={zoneState.enabled}
                onChange={(event) =>
                  setZoneState((current) => ({ ...current, enabled: event.target.checked }))
                }
                type="checkbox"
              />
              启用
            </label>
            <label className="stacked-control">
              Video ID
              <input
                onChange={(event) =>
                  setZoneState((current) => ({ ...current, videoId: event.target.value }))
                }
                value={zoneState.videoId}
              />
            </label>
            <label className="stacked-control">
              Camera ID
              <input
                onChange={(event) =>
                  setZoneState((current) => ({ ...current, cameraId: event.target.value }))
                }
                value={zoneState.cameraId}
              />
            </label>
            <label className="stacked-control">
              允许角度
              <input
                onChange={(event) =>
                  setZoneState((current) => ({
                    ...current,
                    allowedAngle: Number(event.target.value)
                  }))
                }
                type="number"
                value={zoneState.allowedAngle}
              />
            </label>
            <label className="stacked-control">
              逆行阈值
              <input
                onChange={(event) =>
                  setZoneState((current) => ({
                    ...current,
                    reverseAngleThreshold: Number(event.target.value)
                  }))
                }
                type="number"
                value={zoneState.reverseAngleThreshold}
              />
            </label>
            <label className="stacked-control">
              进入方向
              <select
                onChange={(event) =>
                  setZoneState((current) => ({
                    ...current,
                    inDirection: event.target.value as ZoneEditorState["inDirection"]
                  }))
                }
                value={zoneState.inDirection}
              >
                <option value="any">任意</option>
                <option value="positive">正向</option>
                <option value="negative">反向</option>
              </select>
            </label>
          </div>
          <div className="button-group">
            <button disabled={savingZone} onClick={handleSaveZone} type="button">
              {savingZone ? "保存中..." : "保存区域"}
            </button>
            <button
              className="button-danger"
              disabled={!zoneState.id || savingZone}
              onClick={handleDeleteZone}
              type="button"
            >
              删除区域
            </button>
          </div>
        </section>
      </div>

      <section className="panel">
        <div className="section-heading-row">
          <h3>已保存区域</h3>
          <button onClick={loadConfig} type="button">
            刷新
          </button>
        </div>
        {zones.length === 0 && !loading ? <p className="empty-state">暂无已保存区域。</p> : null}
        {zones.length > 0 ? (
          <table>
            <thead>
              <tr>
                <th>名称</th>
                <th>类型</th>
                <th>启用</th>
                <th>版本</th>
                <th>几何</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {zones.map((zone) => (
                <tr className={zoneState.id === zone.id ? "selected-row" : ""} key={zone.id}>
                  <td>{zone.name}</td>
                  <td>{formatZoneTypeLabel(zone.zone_type)}</td>
                  <td>{zone.enabled ? "启用" : "停用"}</td>
                  <td>{zone.version}</td>
                  <td>
                    多边形 {zone.polygon.length} · 方向线 {zone.direction ? "有" : "无"} ·
                    计数线 {zone.counting_line ? "有" : "无"}
                  </td>
                  <td>
                    <button onClick={() => setZoneStateFromZone(zone)} type="button">
                      编辑
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </section>

      <section className="panel">
        <div className="section-heading-row">
          <h3>{ruleState.id ? "编辑事件规则" : "新建事件规则"}</h3>
          <button onClick={() => setRuleState(createEmptyEventRuleFormState())} type="button">
            新建规则
          </button>
        </div>
        <div className="rule-form-grid">
          <label className="stacked-control">
            名称
            <input
              onChange={(event) =>
                setRuleState((current) => ({ ...current, name: event.target.value }))
              }
              value={ruleState.name}
            />
          </label>
          <label className="stacked-control">
            事件类型
            <select
              onChange={(event) =>
                setRuleState((current) => ({ ...current, eventType: event.target.value }))
              }
              value={ruleState.eventType}
            >
              {EVENT_TYPES.map((eventType) => (
                <option key={eventType} value={eventType}>
                  {eventType}
                </option>
              ))}
            </select>
          </label>
          <label className="stacked-control">
            区域
            <select
              onChange={(event) =>
                setRuleState((current) => ({ ...current, zoneId: event.target.value }))
              }
              value={ruleState.zoneId}
            >
              <option value="">无</option>
              {zones.map((zone) => (
                <option key={zone.id} value={zone.id}>
                  {zone.name}
                </option>
              ))}
            </select>
          </label>
          <label className="stacked-control">
            严重程度
            <select
              onChange={(event) =>
                setRuleState((current) => ({ ...current, severity: event.target.value }))
              }
              value={ruleState.severity}
            >
              {EVENT_RULE_SEVERITIES.map((severity) => (
                <option key={severity} value={severity}>
                  {formatSeverityLabel(severity)}
                </option>
              ))}
            </select>
          </label>
          <label className="stacked-control">
            目标类别
            <input
              onChange={(event) =>
                setRuleState((current) => ({
                  ...current,
                  targetClassesText: event.target.value
                }))
              }
              value={ruleState.targetClassesText}
            />
          </label>
          <label className="stacked-control">
            冷却秒数
            <input
              min="0"
              onChange={(event) =>
                setRuleState((current) => ({
                  ...current,
                  cooldownSeconds: Number(event.target.value)
                }))
              }
              type="number"
              value={ruleState.cooldownSeconds}
            />
          </label>
          <label className="stacked-control">
            版本
            <input
              min="1"
              onChange={(event) =>
                setRuleState((current) => ({ ...current, version: Number(event.target.value) }))
              }
              type="number"
              value={ruleState.version}
            />
          </label>
          <label className="stacked-control">
            最小轨迹长度
            <input
              min="1"
              onChange={(event) =>
                setRuleState((current) => ({
                  ...current,
                  minTrackLength: Number(event.target.value)
                }))
              }
              type="number"
              value={ruleState.minTrackLength}
            />
          </label>
          <label className="inline-control">
            <input
              checked={ruleState.enabled}
              onChange={(event) =>
                setRuleState((current) => ({ ...current, enabled: event.target.checked }))
              }
              type="checkbox"
            />
            启用
          </label>
        </div>
        <label className="stacked-control">
          参数 JSON
          <textarea
            onChange={(event) =>
              setRuleState((current) => ({ ...current, parametersText: event.target.value }))
            }
            rows={5}
            value={ruleState.parametersText}
          />
        </label>
        <div className="button-group">
          <button disabled={savingRule} onClick={handleSaveRule} type="button">
            {savingRule ? "保存中..." : "保存规则"}
          </button>
          <button
            className="button-danger"
            disabled={!ruleState.id || savingRule}
            onClick={handleDeleteRule}
            type="button"
          >
            删除规则
          </button>
        </div>
      </section>

      <section className="panel">
        <h3>事件规则</h3>
        {rules.length === 0 && !loading ? <p className="empty-state">暂无已保存事件规则。</p> : null}
        {rules.length > 0 ? (
          <table>
            <thead>
              <tr>
                <th>名称</th>
                <th>类型</th>
                <th>区域</th>
                <th>启用</th>
                <th>严重程度</th>
                <th>版本</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((rule) => (
                <tr className={ruleState.id === rule.id ? "selected-row" : ""} key={rule.id}>
                  <td>{rule.name}</td>
                  <td>{rule.event_type}</td>
                  <td>{rule.zone_id ?? "-"}</td>
                  <td>{rule.enabled ? "启用" : "停用"}</td>
                  <td>{formatSeverityLabel(rule.severity)}</td>
                  <td>{rule.version}</td>
                  <td>
                    <button onClick={() => setRuleState(eventRuleToFormState(rule))} type="button">
                      编辑
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </section>
    </div>
  );

  function setZoneStateFromZone(zone: ZoneRecord) {
    setZoneState(zoneToEditorState(zone));
    setError(null);
    setMessage(null);
  }
}

function SvgEditorLine({ line, variant }: { line: EditorLine; variant: "direction" | "counting" }) {
  if (!line.start) {
    return null;
  }
  return (
    <>
      {line.end ? (
        <line
          className={variant === "direction" ? "zone-direction-line" : "zone-counting-line"}
          x1={line.start.x}
          x2={line.end.x}
          y1={line.start.y}
          y2={line.end.y}
        />
      ) : null}
      <circle className={`${variant}-point`} cx={line.start.x} cy={line.start.y} r="6" />
      {line.end ? (
        <circle className={`${variant}-point`} cx={line.end.x} cy={line.end.y} r="6" />
      ) : null}
    </>
  );
}

function formatLineState(line: EditorLine): string {
  if (line.start && line.end) {
    return "2 个点";
  }
  if (line.start) {
    return "1 个点";
  }
  return "-";
}

function formatDrawingModeLabel(mode: DrawingMode): string {
  const labels: Record<DrawingMode, string> = {
    polygon: "多边形",
    direction: "方向线",
    counting: "计数线"
  };
  return labels[mode];
}

function formatZoneTypeLabel(zoneType: string): string {
  const labels: Record<string, string> = {
    roi: "ROI 区域",
    vehicle_lane: "机动车道",
    no_parking_zone: "禁停区",
    danger_zone: "危险区",
    counting_zone: "计数区"
  };
  return labels[zoneType] ?? zoneType;
}

function formatSeverityLabel(severity: string): string {
  const labels: Record<string, string> = {
    low: "低",
    medium: "中",
    high: "高"
  };
  return labels[severity] ?? severity;
}
