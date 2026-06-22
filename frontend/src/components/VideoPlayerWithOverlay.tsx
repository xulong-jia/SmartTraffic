interface VideoPlayerWithOverlayProps {
  title: string;
}

export default function VideoPlayerWithOverlay({ title }: VideoPlayerWithOverlayProps) {
  return <div className="video-frame">{title}</div>;
}
