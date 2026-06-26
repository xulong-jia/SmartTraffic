from app.models import Detection
from app.repositories.base import BaseRepository


class DetectionRepository(BaseRepository[Detection]):
    model = Detection
