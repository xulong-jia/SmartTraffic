from app.models import Alert
from app.repositories.base import BaseRepository


class AlertRepository(BaseRepository[Alert]):
    model = Alert

    def update_status(self, alert_id: str, status: str) -> Alert | None:
        return self.update(alert_id, status=status)
