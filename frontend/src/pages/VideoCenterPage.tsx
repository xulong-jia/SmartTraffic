import { useEffect, useState } from "react";

import { listVideos } from "../api/videos";
import type { VideoRecord } from "../types";

export default function VideoCenterPage() {
  const [videos, setVideos] = useState<VideoRecord[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    listVideos()
      .then(setVideos)
      .catch((currentError: Error) => setError(currentError.message));
  }, []);

  return (
    <>
      <header className="page-header">
        <div>
          <h2>Video Center</h2>
          <p>视频资产与处理状态</p>
        </div>
      </header>
      <section className="panel">
        {error ? <p>{error}</p> : null}
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
              </tr>
            </thead>
            <tbody>
              {videos.map((video) => (
                <tr key={video.id}>
                  <td>{video.filename}</td>
                  <td>{video.status}</td>
                  <td>{video.fps}</td>
                  <td>{video.total_frames}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </>
  );
}
