import type { FrameDetectionResult } from "../types";
import {
  filterReportOverlayItems,
  filterDetectionsForTime,
  formatOverlayLabel,
  isTrackHighlighted,
  normalizeBbox
} from "../utils/videoOverlay";

interface DetectionOverlayProps {
  frames: FrameDetectionResult[];
  currentTimeMs: number;
  reportMode?: boolean;
  selectedTrackId?: number | null;
  showLabels?: boolean;
}

export default function DetectionOverlay({
  frames,
  currentTimeMs,
  reportMode = false,
  selectedTrackId = null,
  showLabels = true
}: DetectionOverlayProps) {
  const currentDetections = filterDetectionsForTime(frames, currentTimeMs);
  const detections = reportMode
    ? filterReportOverlayItems(currentDetections)
    : currentDetections;
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
        return (
          <g className={highlighted ? "overlay-item highlighted" : "overlay-item"} key={index}>
            <rect
              className="detection-box"
              height={Math.max(0, Number(y2) - Number(y1))}
              width={Math.max(0, Number(x2) - Number(x1))}
              x={Number(x1)}
              y={Number(y1)}
            />
            {showLabels ? (
              <text className="overlay-label" x={Number(x1)} y={Math.max(14, Number(y1) - 6)}>
                {formatOverlayLabel({ className, confidence: detection.confidence })}
              </text>
            ) : null}
          </g>
        );
      })}
    </g>
  );
}
