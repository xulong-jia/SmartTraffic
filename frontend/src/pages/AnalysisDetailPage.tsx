import DetectionOverlay from "../components/DetectionOverlay";
import EventTimeline from "../components/EventTimeline";
import TrackOverlay from "../components/TrackOverlay";
import VideoPlayerWithOverlay from "../components/VideoPlayerWithOverlay";

export default function AnalysisDetailPage() {
  return (
    <>
      <header className="page-header">
        <div>
          <h2>Analysis Detail</h2>
          <p>视频、检测、跟踪、轨迹和事件时间轴</p>
        </div>
      </header>
      <div className="grid two">
        <VideoPlayerWithOverlay title="Video overlay" />
        <div className="grid">
          <DetectionOverlay />
          <TrackOverlay />
          <EventTimeline />
        </div>
      </div>
    </>
  );
}
