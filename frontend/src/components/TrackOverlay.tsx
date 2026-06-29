import type { FrameTrackingResult, TrajectoryFrame } from "../types";
import {
  filterTracksForTime,
  formatOverlayLabel,
  groupTrajectoryPolylines,
  isTrackHighlighted,
  normalizeBbox
} from "../utils/videoOverlay";

interface TrackOverlayProps {
  frames: FrameTrackingResult[];
  trajectoryFrames: TrajectoryFrame[];
  currentTimeMs: number;
  selectedTrackId?: number | null;
  showLabels?: boolean;
}

export default function TrackOverlay({
  frames,
  trajectoryFrames,
  currentTimeMs,
  selectedTrackId = null,
  showLabels = true
}: TrackOverlayProps) {
  const tracks = filterTracksForTime(frames, currentTimeMs);
  const polylines = groupTrajectoryPolylines(trajectoryFrames, currentTimeMs, selectedTrackId);

  if (tracks.length === 0 && polylines.length === 0) {
    return null;
  }

  return (
    <g className="track-overlay">
      {polylines.map((polyline) =>
        polyline.points.length > 1 ? (
          <polyline
            className={polyline.highlighted ? "track-polyline highlighted" : "track-polyline"}
            key={polyline.trackId}
            points={polyline.points.map((point) => `${point.x},${point.y}`).join(" ")}
          />
        ) : null
      )}
      {tracks.map((track, index) => {
        const bbox = normalizeBbox(track.bbox ?? track.metadata ?? track);
        if (!bbox) {
          return null;
        }
        const [x1, y1, x2, y2] = bbox;
        const highlighted = isTrackHighlighted(track.track_id, selectedTrackId);
        const trackId = track.track_id ?? null;
        const className = track.class_name || track.state || "track";
        return (
          <g
            className={highlighted ? "overlay-item highlighted" : "overlay-item"}
            key={[trackId, className, ...bbox, index].join("-")}
          >
            <rect
              className="track-box"
              height={Math.max(0, Number(y2) - Number(y1))}
              width={Math.max(0, Number(x2) - Number(x1))}
              x={Number(x1)}
              y={Number(y1)}
            />
            {showLabels ? (
              <text className="overlay-label track-label" x={Number(x1)} y={Number(y2) + 16}>
                {formatOverlayLabel({ trackId, className, confidence: track.confidence })}
              </text>
            ) : null}
          </g>
        );
      })}
    </g>
  );
}
