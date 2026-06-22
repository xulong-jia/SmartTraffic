from app.cv.yolo_detector import YoloDetector


class DetectionService:
    def __init__(self, detector: YoloDetector | None = None) -> None:
        self.detector = detector or YoloDetector(dry_run=True)
