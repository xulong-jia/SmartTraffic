import type { FrameDetectionResult } from "../types";
import { filterDetectionsForTime, formatConfidence, isTrackHighlighted } from "../utils/videoOverlay";

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
        const [x1, y1, x2, y2] = detection.bbox;
        const highlighted = isTrackHighlighted(index, selectedTrackId);
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
              {detection.class_name} {formatConfidence(detection.confidence)}
            </text>
          </g>
        );
      })}
    </g>
  );
}
