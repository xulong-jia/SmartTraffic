from pydantic import BaseModel


class Alert(BaseModel):
    id: str
    event_id: str
    alert_type: str
    level: str
    status: str
