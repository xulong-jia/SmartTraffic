from app.models import FlowCount, TrafficAnalysisRun, ZoneStatistic
from app.repositories.base import BaseRepository


class TrafficAnalysisRunRepository(BaseRepository[TrafficAnalysisRun]):
    model = TrafficAnalysisRun


class FlowCountRepository(BaseRepository[FlowCount]):
    model = FlowCount


class ZoneStatisticRepository(BaseRepository[ZoneStatistic]):
    model = ZoneStatistic
