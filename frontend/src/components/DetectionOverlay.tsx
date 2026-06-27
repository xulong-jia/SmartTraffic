import type { FrameDetectionResult } from "../types";
import {
  filterDetectionsForTime,
  formatConfidence,
  isTrackHighlighted,
  normalizeBbox
} from "../utils/videoOverlay";

interface DetectionOverlayProps {
  frames: FrameDetectionResult[];
  currentTimeMs: number;
  selectedTrackId?: number | null;
}

export default function DetectionOverlay({
  frames,
  currentTimeMs,
  selectedTrackId = null
}: DetectionOverlayProps) {
  const detections = filterDetectionsForTime(frames, currentTimeMs);
  if (detections.length === 0) {
    return null;
  }

  return (
    <g className="detection-overlay">
      {detections.map((detection, index) => {
        const bbox = normalizeBbox(detection.bbox ?? detection);
        if (!bbox) {
          return null;
        }
        const [x1, y1, x2, y2] = bbox;
        const highlighted = isTrackHighlighted(index, selectedTrackId);
        const className = detection.class_name || "object";
        const confidence = Number.isFinite(Number(detection.confidence))
          ? Number(detection.confidence)
          : null;
        return (
          <g className={highlighted ? "overlay-item highlighted" : "overlay-item"} key={index}>
            <rect
              className="detection-box"
              height={Math.max(0, Number(y2) - Number(y1))}
              width={Math.max(0, Number(x2) - Number(x1))}
              x={Number(x1)}
              y={Number(y1)}
            />
            <text className="overlay-label" x={Number(x1)} y={Math.max(14, Number(y1) - 6)}>
              {className} {formatConfidence(confidence)}
            </text>
          </g>
        );
      })}
    </g>
  );
}
