export interface EditorPoint {
  x: number;
  y: number;
}

export interface EditorLine {
  start: EditorPoint | null;
  end: EditorPoint | null;
}

export function clampCoordinate(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) {
    return min;
  }
  return Math.min(Math.max(value, min), max);
}

export function clampPoint(point: EditorPoint, width: number, height: number): EditorPoint {
  return {
    x: clampCoordinate(point.x, 0, width),
    y: clampCoordinate(point.y, 0, height)
  };
}

export function toApiPoint(point: EditorPoint): number[] {
  return [roundCoordinate(point.x), roundCoordinate(point.y)];
}

export function fromApiPoint(point: number[] | null | undefined): EditorPoint | null {
  if (!Array.isArray(point) || point.length !== 2) {
    return null;
  }
  const [x, y] = point;
  if (!Number.isFinite(x) || !Number.isFinite(y)) {
    return null;
  }
  return { x: Number(x), y: Number(y) };
}

export function toApiPolygon(points: EditorPoint[]): number[][] {
  return points.map(toApiPoint);
}

export function fromApiPolygon(points: number[][] | null | undefined): EditorPoint[] {
  if (!Array.isArray(points)) {
    return [];
  }
  return points
    .map((point) => fromApiPoint(point))
    .filter((point): point is EditorPoint => point !== null);
}

export function isValidPolygon(points: EditorPoint[]): boolean {
  return points.length >= 3;
}

export function isCompleteLine(line: EditorLine): boolean {
  return line.start !== null && line.end !== null;
}

export function setLinePoint(line: EditorLine, point: EditorPoint): EditorLine {
  if (line.start === null || (line.start !== null && line.end !== null)) {
    return { start: point, end: null };
  }
  return { start: line.start, end: point };
}

export function lineAngleDegrees(line: EditorLine): number | null {
  if (!isCompleteLine(line) || line.start === null || line.end === null) {
    return null;
  }
  const dx = line.end.x - line.start.x;
  const dy = line.end.y - line.start.y;
  if (dx === 0 && dy === 0) {
    return null;
  }
  const angle = (Math.atan2(dy, dx) * 180) / Math.PI;
  return roundCoordinate((angle + 360) % 360);
}

function roundCoordinate(value: number): number {
  return Math.round(value * 1000) / 1000;
}
