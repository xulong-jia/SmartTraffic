import type { MouseEvent } from "react";

import type { EventRecord } from "../types";
import {
  buildEventTableRows,
  eventTableEmptyLabel,
  filterEventTableRows,
  getEventTableId,
  sortEventTableRows
} from "../utils/eventTable";

interface EventTableProps {
  events: EventRecord[];
  loading?: boolean;
  error?: string;
  statusFilter?: string | null;
  eventTypeFilter?: string | null;
  severityFilter?: string | null;
  selectedEventId?: string | null;
  maxRows?: number;
  onSelectEvent?: (eventId: string, event: EventRecord) => void;
  buildReviewHref?: (event: EventRecord) => string | null;
  onOpenReview?: (href: string) => void;
}

export default function EventTable({
  events,
  loading = false,
  error = "",
  statusFilter = "",
  eventTypeFilter = "",
  severityFilter = "",
  selectedEventId = null,
  maxRows = 20,
  onSelectEvent,
  buildReviewHref,
  onOpenReview
}: EventTableProps) {
  const visibleEvents = sortEventTableRows(
    filterEventTableRows(events, {
      status: statusFilter,
      eventType: eventTypeFilter,
      severity: severityFilter
    })
  ).slice(0, maxRows);
  const rows = buildEventTableRows(visibleEvents, selectedEventId);
  const emptyLabel = eventTableEmptyLabel(loading, error, visibleEvents);

  return (
    <div>
      {emptyLabel ? <p className="muted">{emptyLabel}</p> : null}
      {rows.length > 0 ? (
        <table>
          <caption className="sr-only">事件列表</caption>
          <thead>
            <tr>
              <th scope="col">类型</th>
              <th scope="col">严重程度</th>
              <th scope="col">状态</th>
              <th scope="col">Track</th>
              <th scope="col">区域</th>
              <th scope="col">开始</th>
              <th scope="col">Run</th>
              <th scope="col">操作</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => {
              const event = visibleEvents[index];
              const eventId = getEventTableId(event, index);
              const href = buildReviewHref?.(event) ?? null;
              return (
                <tr
                  className={row.selected ? "selected-row" : ""}
                  key={row.id}
                >
                  <td>{row.eventType}</td>
                  <td>{row.severity}</td>
                  <td>{row.status}</td>
                  <td>{row.trackId}</td>
                  <td>{row.zoneId}</td>
                  <td>{row.startTimeMs}</td>
                  <td className="cell-id">{row.runId}</td>
                  <td>
                    <div className="button-group">
                      {onSelectEvent ? (
                        <button type="button" onClick={() => onSelectEvent(eventId, event)}>
                          查看
                        </button>
                      ) : null}
                      {href ? (
                        <a
                          href={href}
                          onClick={(clickEvent) => openReviewLink(clickEvent, href, onOpenReview)}
                        >
                          复核
                        </a>
                      ) : (
                        <span className="muted">无 event_id</span>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : null}
    </div>
  );
}

function openReviewLink(
  event: MouseEvent<HTMLAnchorElement>,
  href: string,
  onOpenReview?: (href: string) => void
) {
  if (!onOpenReview || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
    return;
  }
  event.preventDefault();
  event.stopPropagation();
  onOpenReview(href);
}
