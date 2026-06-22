import { useEffect, useState } from "react";

import { getAnalysisRunDetections, listAnalysisRuns } from "../api/analysisRuns";
import VideoPlayerWithOverlay from "../components/VideoPlayerWithOverlay";
import type { AnalysisRun, AnalysisRunDetections } from "../types";

export default function AnalysisDetailPage() {
  const [runs, setRuns] = useState<AnalysisRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState("");
  const [detections, setDetections] = useState<AnalysisRunDetections | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    listAnalysisRuns()
      .then((items) => {
        setRuns(items);
        if (items.length > 0) {
          setSelectedRunId(items[items.length - 1].id);
        }
      })
      .catch((currentError: Error) => setError(currentError.message));
  }, []);

  useEffect(() => {
    if (!selectedRunId) {
      return;
    }
    getAnalysisRunDetections(selectedRunId, 50)
      .then(setDetections)
      .catch((currentError: Error) => setError(currentError.message));
  }, [selectedRunId]);

  return (
    <>
      <header className="page-header">
        <div>
          <h2>Analysis Detail</h2>
          <p>阶段二检测结果</p>
        </div>
      </header>
      <div className="grid two">
        <VideoPlayerWithOverlay title="Detection preview placeholder" />
        <div className="grid">
          <section className="panel">
            <label>
              Run ID
              <select value={selectedRunId} onChange={(event) => setSelectedRunId(event.target.value)}>
                <option value="">No run selected</option>
                {runs.map((run) => (
                  <option key={run.id} value={run.id}>
                    {run.id}
                  </option>
                ))}
              </select>
            </label>
            {error ? <p>{error}</p> : null}
          </section>
          {detections ? (
            <section className="panel">
              <h3>Detection Summary</h3>
              <p>
                {detections.summary.total_frames_processed} frames ·{" "}
                {detections.summary.total_detections} detections
              </p>
              <h3>Frame Results</h3>
              <table>
                <thead>
                  <tr>
                    <th>Frame</th>
                    <th>Timestamp</th>
                    <th>Detections</th>
                  </tr>
                </thead>
                <tbody>
                  {detections.frames.map((frame) => (
                    <tr key={frame.frame_index}>
                      <td>{frame.frame_index}</td>
                      <td>{frame.timestamp_ms ?? 0} ms</td>
                      <td>{frame.detections.length}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          ) : null}
        </div>
      </div>
    </>
  );
}
