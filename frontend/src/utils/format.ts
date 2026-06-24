export function formatSeconds(seconds: number): string {
  return `${seconds.toFixed(1)}s`;
}

export function formatDisplayValue(value: unknown, fallback = "-"): string {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  if (typeof value === "number" && !Number.isFinite(value)) {
    return fallback;
  }
  if (Array.isArray(value) || typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}
