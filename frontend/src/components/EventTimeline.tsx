import { useState } from "react";
import type { EventRecord } from "../types";
import {
  filterEvents,
  getEventId,
  getEventSeekTimeMs,
  uniqueEventValues
} from "../utils/eventTimeline";
import { formatDisplayValue as formatValue } from "../utils/format";

interface EventTimelineProps {
  events: EventRecord[];
  selectedEventId?: string | null;
  loading?: boolean;
  error?: string;
  onSelectEvent: (eventId: string, event: EventRecord) => void;
  onSeek: (timeMs: number) => void;
}

export default function EventTimeline({
  events,
  selectedEventId = null,
  loading = false,
  error = "",
  onSelectEvent,
  onSeek
}: EventTimelineProps) {
  const [eventTypeFilter, setEventTypeFilter] = useState("");
  const [severityFilter, setSeverityFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const visibleEvents = filterEvents(events, {
    eventType: eventTypeFilter || undefined,
    severity: severityFilter || undefined,
    status: statusFilter || undefined
  });

  return (
    <section className="panel event-timeline">
      <div className="section-heading-row">
        <h3>事件时间线</h3>
        <span className="status-pill">{visibleEvents.length} 个事件</span>
      </div>
      <div className="toolbar compact">
        <label>
          类型
          <select value={eventTypeFilter} onChange={(event) => setEventTypeFilter(event.target.value)}>
            <option value="">全部</option>
            {uniqueEventValues(events, "event_type").map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
        <label>
          严重程度
          <select value={severityFilter} onChange={(event) => setSeverityFilter(event.target.value)}>
            <option value="">全部</option>
            {uniqueEventValues(events, "severity").map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
        <label>
          状态
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            <option value="">全部</option>
            {uniqueEventValues(events, "status").map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
      </div>
      {loading ? <p className="muted">正在加载事件...</p> : null}
      {error ? <p>{error}</p> : null}
      {visibleEvents.length === 0 && !loading ? <p className="muted">暂无事件。请先运行一次视频分析。</p> : null}
      {visibleEvents.length > 0 ? (
        <div className="timeline-list">
          {visibleEvents.map((event, index) => {
            const eventId = getEventId(event, index);
            const selected = eventId === selectedEventId;
            const seekTime = getEventSeekTimeMs(event);
            return (
              <button
                className={selected ? "timeline-item selected" : "timeline-item"}
                key={eventId}
                onClick={() => {
                  onSelectEvent(eventId, event);
                  onSeek(seekTime);
                }}
                type="button"
              >
                <span className="timeline-time">{Math.round(seekTime)} ms</span>
                <span className="timeline-main">{formatValue(event.event_type)}</span>
                <span className="timeline-meta">
                  {formatValue(event.severity)} · {formatValue(event.status)} · track_id{" "}
                  {formatValue(event.track_id)} · zone_id {formatValue(event.zone_id)}
                </span>
              </button>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}
