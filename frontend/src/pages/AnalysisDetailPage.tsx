import { useEffect, useState } from "react";

import {
  getAnalysisRunDetections,
  getAnalysisRunTracks,
  listAnalysisRuns
} from "../api/analysisRuns";
import VideoPlayerWithOverlay from "../components/VideoPlayerWithOverlay";
import type { AnalysisRun, AnalysisRunDetections, AnalysisRunTracks } from "../types";

export default function AnalysisDetailPage() {
  const [runs, setRuns] = useState<AnalysisRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState("");
  const [detections, setDetections] = useState<AnalysisRunDetections | null>(null);
  const [tracks, setTracks] = useState<AnalysisRunTracks | null>(null);
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
    Promise.all([
      getAnalysisRunDetections(selectedRunId, 50),
      getAnalysisRunTracks(selectedRunId, 50)
    ])
      .then(([detectionPayload, trackingPayload]) => {
        setDetections(detectionPayload);
        setTracks(trackingPayload);
      })
      .catch((currentError: Error) => setError(currentError.message));
  }, [selectedRunId]);

  return (
    <>
      <header className="page-header">
        <div>
          <h2>Analysis Detail</h2>
          <p>阶段三检测与跟踪结果</p>
        </div>
      </header>
      <div className="grid two">
        <VideoPlayerWithOverlay title="Tracking preview placeholder" />
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
          {tracks ? (
            <section className="panel">
              <h3>Tracking Summary</h3>
              <p>
                {tracks.summary.total_frames_processed} frames · {tracks.summary.total_tracks} track rows ·{" "}
                {tracks.summary.unique_track_ids} unique IDs
              </p>
              <h3>Track Results</h3>
              <table>
                <thead>
                  <tr>
                    <th>Frame</th>
                    <th>Track ID</th>
                    <th>Class</th>
                    <th>State</th>
                  </tr>
                </thead>
                <tbody>
                  {tracks.rows.slice(0, 20).map((track, index) => (
                    <tr key={`${track.frame_index}-${track.track_id}-${index}`}>
                      <td>{track.frame_index}</td>
                      <td>{track.track_id}</td>
                      <td>{track.class_name}</td>
                      <td>{track.state}</td>
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
