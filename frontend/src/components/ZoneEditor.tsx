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
      setMessage(`Zone ${saved.name} saved.`);
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
      setMessage("Zone deleted.");
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
      setMessage(`Event rule ${saved.name} saved.`);
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
      setMessage("Event rule deleted.");
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Failed to delete rule.");
    } finally {
      setSavingRule(false);
    }
  }

  return (
    <div className="zone-editor">
      {loading ? <div className="panel muted">Loading zone and rule config...</div> : null}
      {error ? <div className="panel status-error">{error}</div> : null}
      {message ? <div className="panel status-available">{message}</div> : null}

      <div className="grid zone-editor-grid">
        <section className="panel zone-editor-canvas-panel">
          <div className="section-heading-row">
            <div>
              <h3>Zone Canvas</h3>
              <p className="muted">
                {mode === "polygon"
                  ? "Polygon geometry"
                  : mode === "direction"
                    ? "Direction line geometry"
                    : "Counting line geometry"}
              </p>
            </div>
            <div className="toolbar compact">
              {DRAWING_MODES.map((drawingMode) => (
                <button
                  className={mode === drawingMode ? "active-control" : ""}
                  key={drawingMode}
                  onClick={() => setMode(drawingMode)}
                  type="button"
                >
                  {drawingMode}
                </button>
              ))}
              <button
                onClick={() => setZoneState((current) => clearDrawingForMode(current, mode))}
                type="button"
              >
                Clear
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
            <span>Polygon points: {zoneState.polygon.length}</span>
            <span>Direction angle: {lineAngleDegrees(zoneState.directionLine) ?? "-"}</span>
            <span>Counting line: {formatLineState(zoneState.countingLine)}</span>
          </div>
        </section>

        <section className="panel">
          <div className="section-heading-row">
            <h3>{zoneState.id ? "Edit Zone" : "New Zone"}</h3>
            <button onClick={() => setZoneState(createEmptyZoneEditorState())} type="button">
              New
            </button>
          </div>
          <div className="zone-form-grid">
            <label className="stacked-control">
              Name
              <input
                onChange={(event) =>
                  setZoneState((current) => ({ ...current, name: event.target.value }))
                }
                value={zoneState.name}
              />
            </label>
            <label className="stacked-control">
              Type
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
                    {zoneType}
                  </option>
                ))}
              </select>
            </label>
            <label className="stacked-control">
              Version
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
              Enabled
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
              Allowed angle
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
              Reverse threshold
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
              In direction
              <select
                onChange={(event) =>
                  setZoneState((current) => ({
                    ...current,
                    inDirection: event.target.value as ZoneEditorState["inDirection"]
                  }))
                }
                value={zoneState.inDirection}
              >
                <option value="any">any</option>
                <option value="positive">positive</option>
                <option value="negative">negative</option>
              </select>
            </label>
          </div>
          <div className="toolbar compact">
            <button disabled={savingZone} onClick={handleSaveZone} type="button">
              {savingZone ? "Saving..." : "Save Zone"}
            </button>
            <button disabled={!zoneState.id || savingZone} onClick={handleDeleteZone} type="button">
              Delete Zone
            </button>
          </div>
        </section>
      </div>

      <section className="panel">
        <div className="section-heading-row">
          <h3>Saved Zones</h3>
          <button onClick={loadConfig} type="button">
            Refresh
          </button>
        </div>
        {zones.length === 0 && !loading ? <p className="muted">No zones saved yet.</p> : null}
        {zones.length > 0 ? (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Enabled</th>
                <th>Version</th>
                <th>Geometry</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {zones.map((zone) => (
                <tr className={zoneState.id === zone.id ? "selected-row" : ""} key={zone.id}>
                  <td>{zone.name}</td>
                  <td>{zone.zone_type}</td>
                  <td>{zone.enabled ? "enabled" : "disabled"}</td>
                  <td>{zone.version}</td>
                  <td>
                    polygon {zone.polygon.length} · direction {zone.direction ? "yes" : "no"} ·
                    counting {zone.counting_line ? "yes" : "no"}
                  </td>
                  <td>
                    <button onClick={() => setZoneStateFromZone(zone)} type="button">
                      Edit
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
          <h3>{ruleState.id ? "Edit Event Rule" : "New Event Rule"}</h3>
          <button onClick={() => setRuleState(createEmptyEventRuleFormState())} type="button">
            New Rule
          </button>
        </div>
        <div className="rule-form-grid">
          <label className="stacked-control">
            Name
            <input
              onChange={(event) =>
                setRuleState((current) => ({ ...current, name: event.target.value }))
              }
              value={ruleState.name}
            />
          </label>
          <label className="stacked-control">
            Event type
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
            Zone
            <select
              onChange={(event) =>
                setRuleState((current) => ({ ...current, zoneId: event.target.value }))
              }
              value={ruleState.zoneId}
            >
              <option value="">none</option>
              {zones.map((zone) => (
                <option key={zone.id} value={zone.id}>
                  {zone.name}
                </option>
              ))}
            </select>
          </label>
          <label className="stacked-control">
            Severity
            <select
              onChange={(event) =>
                setRuleState((current) => ({ ...current, severity: event.target.value }))
              }
              value={ruleState.severity}
            >
              <option value="low">low</option>
              <option value="medium">medium</option>
              <option value="high">high</option>
              <option value="critical">critical</option>
            </select>
          </label>
          <label className="stacked-control">
            Target classes
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
            Cooldown seconds
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
            Version
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
            Min track length
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
            Enabled
          </label>
        </div>
        <label className="stacked-control">
          Parameters JSON
          <textarea
            onChange={(event) =>
              setRuleState((current) => ({ ...current, parametersText: event.target.value }))
            }
            rows={5}
            value={ruleState.parametersText}
          />
        </label>
        <div className="toolbar compact">
          <button disabled={savingRule} onClick={handleSaveRule} type="button">
            {savingRule ? "Saving..." : "Save Rule"}
          </button>
          <button disabled={!ruleState.id || savingRule} onClick={handleDeleteRule} type="button">
            Delete Rule
          </button>
        </div>
      </section>

      <section className="panel">
        <h3>Event Rules</h3>
        {rules.length === 0 && !loading ? <p className="muted">No event rules saved yet.</p> : null}
        {rules.length > 0 ? (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Zone</th>
                <th>Enabled</th>
                <th>Severity</th>
                <th>Version</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((rule) => (
                <tr className={ruleState.id === rule.id ? "selected-row" : ""} key={rule.id}>
                  <td>{rule.name}</td>
                  <td>{rule.event_type}</td>
                  <td>{rule.zone_id ?? "-"}</td>
                  <td>{rule.enabled ? "enabled" : "disabled"}</td>
                  <td>{rule.severity}</td>
                  <td>{rule.version}</td>
                  <td>
                    <button onClick={() => setRuleState(eventRuleToFormState(rule))} type="button">
                      Edit
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
    return "2 points";
  }
  if (line.start) {
    return "1 point";
  }
  return "-";
}
