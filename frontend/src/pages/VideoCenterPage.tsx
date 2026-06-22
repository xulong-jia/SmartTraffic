import { useEffect, useState } from "react";

import { listVideos, startVideoProcessing, uploadVideo } from "../api/videos";
import type { DetectionProcessResult, VideoRecord } from "../types";

export default function VideoCenterPage() {
  const [videos, setVideos] = useState<VideoRecord[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [lastRun, setLastRun] = useState<DetectionProcessResult | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    refreshVideos();
  }, []);

  function refreshVideos() {
    listVideos()
      .then(setVideos)
      .catch((currentError: Error) => setError(currentError.message));
  }

  async function handleUpload() {
    if (!selectedFile) {
      return;
    }
    setLoading(true);
    setError("");
    try {
      await uploadVideo(selectedFile);
      setSelectedFile(null);
      refreshVideos();
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleProcess(videoId: string) {
    setLoading(true);
    setError("");
    try {
      const result = await startVideoProcessing(videoId, {
        dry_run: true,
        frame_stride: 1,
        max_frames: 120
      });
      setLastRun(result);
      refreshVideos();
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Detection failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <header className="page-header">
        <div>
          <h2>Video Center</h2>
          <p>视频资产与处理状态</p>
        </div>
      </header>
      <section className="panel">
        <div className="toolbar">
          <input
            type="file"
            accept="video/mp4,video/avi,video/quicktime,video/x-matroska,video/webm"
            onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
          />
          <button disabled={!selectedFile || loading} type="button" onClick={handleUpload}>
            Upload
          </button>
        </div>
        {error ? <p>{error}</p> : null}
        {lastRun ? (
          <div className="panel">
            <h3>Latest Detection Run</h3>
            <p>
              <strong>{lastRun.run_id}</strong> · {lastRun.status} ·{" "}
              {lastRun.total_frames_processed} frames · {lastRun.total_detections} detections
            </p>
          </div>
        ) : null}
        {videos.length === 0 ? (
          <p className="muted">暂无视频</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Filename</th>
                <th>Status</th>
                <th>FPS</th>
                <th>Frames</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {videos.map((video) => (
                <tr key={video.id}>
                  <td>{video.filename}</td>
                  <td>{video.status}</td>
                  <td>{video.fps}</td>
                  <td>{video.total_frames}</td>
                  <td>
                    <button disabled={loading} type="button" onClick={() => handleProcess(video.id)}>
                      Detect
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </>
  );
}
