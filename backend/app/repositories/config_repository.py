from app.models import EventRule, Zone
from app.repositories.base import BaseRepository


class ZoneRepository(BaseRepository[Zone]):
    model = Zone


class EventRuleRepository(BaseRepository[EventRule]):
    model = EventRule
