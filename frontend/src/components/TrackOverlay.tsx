import type { FrameTrackingResult, TrajectoryFrame } from "../types";
import {
  filterTracksForTime,
  formatConfidence,
  groupTrajectoryPolylines,
  isTrackHighlighted
} from "../utils/videoOverlay";

interface TrackOverlayProps {
  frames: FrameTrackingResult[];
  trajectoryFrames: TrajectoryFrame[];
  currentTimeMs: number;
  selectedTrackId?: number | null;
}

export default function TrackOverlay({
  frames,
  trajectoryFrames,
  currentTimeMs,
  selectedTrackId = null
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
      {tracks.map((track) => {
        const [x1, y1, x2, y2] = track.bbox;
        const highlighted = isTrackHighlighted(track.track_id, selectedTrackId);
        return (
          <g
            className={highlighted ? "overlay-item highlighted" : "overlay-item"}
            key={`${track.track_id}-${track.class_name}`}
          >
            <rect
              className="track-box"
              height={Math.max(0, Number(y2) - Number(y1))}
              width={Math.max(0, Number(x2) - Number(x1))}
              x={Number(x1)}
              y={Number(y1)}
            />
            <text className="overlay-label track-label" x={Number(x1)} y={Number(y2) + 16}>
              #{track.track_id} {track.class_name} {formatConfidence(track.confidence)}
            </text>
          </g>
        );
      })}
    </g>
  );
}
