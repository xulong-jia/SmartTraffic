import { useEffect, useRef } from "react";
import type {
  EventRecord,
  FrameDetectionResult,
  FrameTrackingResult,
  TrajectoryFrame,
  ZoneRecord
} from "../types";
import DetectionOverlay from "./DetectionOverlay";
import TrackOverlay from "./TrackOverlay";
import {
  filterReportOverlayItems,
  filterTracksForTime,
  isZoneHighlighted,
  zonePolygonPoints
} from "../utils/videoOverlay";

interface VideoPlayerWithOverlayProps {
  title?: string;
  videoUrl?: string | null;
  width?: number;
  height?: number;
  detections?: FrameDetectionResult[];
  tracks?: FrameTrackingResult[];
  trajectoryPoints?: TrajectoryFrame[];
  zones?: ZoneRecord[];
  events?: EventRecord[];
  currentTimeMs: number;
  reportMode?: boolean;
  selectedEventId?: string | null;
  selectedTrackId?: number | null;
  selectedZoneId?: string | null;
  onSeek: (timeMs: number) => void;
}

export default function VideoPlayerWithOverlay({
  title = "视频叠加",
  videoUrl = null,
  width = 960,
  height = 540,
  detections = [],
  tracks = [],
  trajectoryPoints = [],
  zones = [],
  currentTimeMs,
  reportMode = false,
  selectedTrackId = null,
  selectedZoneId = null,
  onSeek
}: VideoPlayerWithOverlayProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const reportTracks = reportMode
    ? filterReportOverlayItems(filterTracksForTime(tracks, currentTimeMs))
    : [];

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !Number.isFinite(currentTimeMs)) {
      return;
    }
    const nextTime = currentTimeMs / 1000;
    if (Math.abs(video.currentTime - nextTime) > 0.25) {
      video.currentTime = Math.max(0, nextTime);
    }
  }, [currentTimeMs]);

  return (
    <section className="panel video-overlay-panel">
      <div className="section-heading-row">
        <h3>{title}</h3>
        <span className="status-pill">{Math.round(currentTimeMs)} ms</span>
      </div>
      <div className="video-overlay-stage" style={{ aspectRatio: `${width} / ${height}` }}>
        {videoUrl ? (
          <video
            className="overlay-video"
            controls
            onTimeUpdate={(event) => onSeek(event.currentTarget.currentTime * 1000)}
            ref={videoRef}
            src={videoUrl}
          />
        ) : (
          <div className="overlay-placeholder">当前任务没有可播放视频 URL</div>
        )}
        <svg
          className="video-overlay-svg"
          preserveAspectRatio="xMidYMid meet"
          viewBox={`0 0 ${width} ${height}`}
        >
          <ZoneOverlay reportMode={reportMode} zones={zones} selectedZoneId={selectedZoneId} />
          <DetectionOverlay
            currentTimeMs={currentTimeMs}
            frames={detections}
            reportMode={reportMode}
            selectedTrackId={selectedTrackId}
            showLabels={!reportMode || reportTracks.length === 0}
          />
          <TrackOverlay
            currentTimeMs={currentTimeMs}
            frames={tracks}
            reportMode={reportMode}
            selectedTrackId={selectedTrackId}
            trajectoryFrames={trajectoryPoints}
          />
        </svg>
      </div>
    </section>
  );
}

function ZoneOverlay({
  reportMode,
  zones,
  selectedZoneId
}: {
  reportMode: boolean;
  zones: ZoneRecord[];
  selectedZoneId: string | null;
}) {
  if (zones.length === 0) {
    return null;
  }
  return (
    <g className="zone-display-overlay">
      {zones.map((zone) => {
        const points = zonePolygonPoints(zone);
        if (points.length < 3) {
          return null;
        }
        const highlighted = isZoneHighlighted(zone.id, selectedZoneId);
        const className = [
          "display-zone",
          zone.enabled ? "enabled" : "disabled",
          highlighted ? "highlighted" : ""
        ]
          .filter(Boolean)
          .join(" ");
        const labelPoint = points[0];
        return (
          <g className={className} key={zone.id}>
            <polygon points={points.map((point) => `${point.x},${point.y}`).join(" ")} />
            {zone.direction?.start_point && zone.direction?.end_point ? (
              <line
                className="zone-direction-display"
                x1={Number(zone.direction.start_point[0])}
                x2={Number(zone.direction.end_point[0])}
                y1={Number(zone.direction.start_point[1])}
                y2={Number(zone.direction.end_point[1])}
              />
            ) : null}
            {zone.counting_line?.start_point && zone.counting_line?.end_point ? (
              <line
                className="zone-counting-display"
                x1={Number(zone.counting_line.start_point[0])}
                x2={Number(zone.counting_line.end_point[0])}
                y1={Number(zone.counting_line.start_point[1])}
                y2={Number(zone.counting_line.end_point[1])}
              />
            ) : null}
            <text className="overlay-label zone-label" x={labelPoint.x} y={labelPoint.y - 8}>
              {reportMode ? zone.name : `${zone.name} · ${zone.zone_type}`}
            </text>
          </g>
        );
      })}
    </g>
  );
}
