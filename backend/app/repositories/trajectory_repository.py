from app.models import TrajectoryPoint
from app.repositories.base import BaseRepository


class TrajectoryPointRepository(BaseRepository[TrajectoryPoint]):
    model = TrajectoryPoint
