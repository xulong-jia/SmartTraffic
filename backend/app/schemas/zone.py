from pydantic import BaseModel


class Zone(BaseModel):
    id: str
    name: str
    zone_type: str
    polygon: list[list[float]]
    enabled: bool = True
