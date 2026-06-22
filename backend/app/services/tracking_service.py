from app.cv.deepsort_tracker import DeepSortTracker


class TrackingService:
    def __init__(self, tracker: DeepSortTracker | None = None) -> None:
        self.tracker = tracker or DeepSortTracker()
