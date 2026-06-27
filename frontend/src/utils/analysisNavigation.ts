export function parseAnalysisRunIdFromSearch(search: string): string {
  const value = new URLSearchParams(search).get("run_id")?.trim();
  return value || "";
}

export function resolveAnalysisInitialRunId(
  selectedAnalysisRunId: string,
  locationSearch: string
): string {
  return parseAnalysisRunIdFromSearch(locationSearch) || selectedAnalysisRunId;
}
