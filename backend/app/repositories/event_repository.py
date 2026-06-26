from app.models import Event, EventEvidence, RuleExecution
from app.repositories.base import BaseRepository


class EventRepository(BaseRepository[Event]):
    model = Event

    def update_status(self, event_id: str, status: str) -> Event | None:
        return self.update(event_id, status=status)


class EventEvidenceRepository(BaseRepository[EventEvidence]):
    model = EventEvidence


class RuleExecutionRepository(BaseRepository[RuleExecution]):
    model = RuleExecution
